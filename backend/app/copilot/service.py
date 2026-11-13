"""Sales copilot (AGENT_ARCHITECTURE §11): brief + email grounded only in validated claims.

The model sees short ids (F1, F2…) for facts/inferences/signals, never raw web pages.
Its output is validated: unknown ids are dropped, inference may not appear in the email.
Without an API key a deterministic template is used.
"""
from __future__ import annotations

import json
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, ValidationFailed
from app.core.vocab import CLAIM_FIELDS, OFFERING_LABELS, SIGNAL_TYPES
from app.llm import gateway as llm
from app.llm import prompts
from app.models import Account, Claim, Company, Contact, CopilotOutput, Property, Signal
from app.workflow.errors import AIQuotaExhausted, PermanentError, TransientError
from app.api.serializers import display_value


def generate(db: Session, *, workspace_id: UUID, user_id: UUID, account: Account, offering: str,
             contact_id: UUID | None, role_code: str | None, tone: str) -> CopilotOutput:
    company = db.get(Company, account.company_id)
    prop = db.get(Property, account.property_id)
    contact = db.get(Contact, contact_id) if contact_id else None
    if company.do_not_contact or (contact and contact.do_not_contact):
        raise Conflict("This company or contact is marked do-not-contact.")
    if offering not in OFFERING_LABELS:
        raise ValidationFailed("Unknown offering")
    claims = db.execute(select(Claim).where(Claim.company_id == company.id, Claim.is_current.is_(True),
                                            Claim.kind.in_(("fact", "inference")))).scalars().all()
    sigs = db.execute(select(Signal).where(Signal.company_id == company.id).order_by(Signal.published_at.desc().nullslast()).limit(5)).scalars().all()
    ref: dict[str, tuple[str, str]] = {}  # short id -> (uuid, kind)
    facts = []
    for i, c in enumerate(claims, 1):
        sid = f"F{i}"
        ref[sid] = (str(c.id), c.kind)
        facts.append({"id": sid, "kind": c.kind, "field": CLAIM_FIELDS.get(c.field, c.field), "value": display_value(c.field, c.value)})
    for i, s in enumerate(sigs, 1):
        sid = f"G{i}"
        ref[sid] = (str(s.id), "fact")
        facts.append({"id": sid, "kind": "fact", "field": "Signal: " + SIGNAL_TYPES.get(s.signal_type, (s.signal_type,))[0],
                      "value": f"{s.title} ({s.published_at.date().isoformat() if s.published_at else 'undated'})"})
    hotel = {"name": prop.name, "brand": prop.brand, "locality": prop.locality, "city": prop.city,
             "lifecycle": prop.lifecycle, "opening_date": prop.opening_date.isoformat() if prop.opening_date else None,
             "rooms": prop.rooms_count, "meeting_rooms": prop.meeting_rooms_count,
             "largest_meeting_capacity": prop.largest_meeting_capacity, "banquet_capacity": prop.banquet_capacity,
             "facilities": prop.facilities, "distance_km": account.distance_km}
    recipient = {"name": contact.full_name, "title": contact.title} if contact else {"role": role_code}
    version = (db.execute(select(func.max(CopilotOutput.version)).where(CopilotOutput.account_id == account.id)).scalar() or 0) + 1

    content, by, pv = None, "template", "template-v1"
    note = "AI drafting is off; this is a template. Personalise it before sending."
    if llm.ai_available():
        pid, ver, system = prompts.COPILOT
        user = (f"Hotel: {json.dumps(hotel, ensure_ascii=False)}\nOffering to propose: {OFFERING_LABELS[offering]} ({offering})\n"
                f"Recipient: {json.dumps(recipient)}\nTone: {tone}\nCompany: {company.name}\nFacts:\n{json.dumps(facts, ensure_ascii=False)}")
        try:
            out = llm.call_json(ctx=llm.CallContext(workspace_id=workspace_id, step="copilot"), prompt_id=pid, version=ver,
                                system=system, user=user, tier="standard", max_output_tokens=6000)
            content, by, pv = _validate(out, ref, offering), "llm", ver
        except (TransientError, PermanentError, ValidationFailed) as e:
            # D-45: the Pitch button always produces a draft. Busy / out-of-allowance AI or an ungroundable draft
            # falls back to the fact-based template and the brief says why. A rejected API key is still an error.
            if isinstance(e, PermanentError) and not isinstance(e, AIQuotaExhausted) and "API key" in str(e):
                raise
            note = ("The AI couldn't write this draft right now, so this is a template built from verified facts. "
                    "Personalise it before sending.")
    elif get_settings().llm_configured:
        note = ("The AI's daily allowance is used up, so this is a template built from verified facts. "
                "Personalise it before sending.")
    if content is None:
        content = _template(company, prop, offering, facts, ref, recipient)
        content["brief"]["approach"] = note
    row = CopilotOutput(workspace_id=workspace_id, account_id=account.id, contact_id=contact_id, offering=offering,
                        version=version, content=content, generated_by=by, prompt_version=pv, created_by=user_id)
    db.add(row)
    return row


def _blocks(items, ref, allow_inference: bool) -> list[dict]:
    out = []
    for b in items or []:
        if isinstance(b, str):
            b = {"text": b, "claims": []}
        text = str(b.get("text", "")).strip()
        if not text:
            continue
        ids = [ref[x] for x in (b.get("claims") or []) if x in ref]
        inf = any(k == "inference" for _, k in ids) or bool(b.get("is_inference"))
        if inf and not allow_inference:
            ids = [x for x in ids if x[1] != "inference"]
            if not ids:
                continue  # an email sentence resting only on inference is dropped
            inf = False
        blk = {"text": text, "claims": [u for u, _ in ids]}
        if inf:
            blk["is_inference"] = True
        out.append(blk)
    return out


def _validate(out: dict, ref: dict, offering: str) -> dict:
    brief = out.get("brief") or {}
    email = out.get("email") or {}
    rec = brief.get("recommended_offering") if brief.get("recommended_offering") in OFFERING_LABELS else offering
    body = _blocks(email.get("body_blocks"), ref, allow_inference=False)
    if not body:
        raise ValidationFailed("The AI draft couldn't be grounded in verified facts. Research the company first, then try again.")
    text_all = " ".join(b["text"] for b in body)
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text_all):
        body = [{**b, "text": re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", b["text"])} for b in body]
    return {"brief": {"summary": _blocks(brief.get("summary"), ref, True), "opportunity": _blocks(brief.get("opportunity"), ref, True),
                      "recommended_offering": rec, "approach": str(brief.get("approach", ""))[:600]},
            "email": {"subject": str(email.get("subject", ""))[:150] or f"Partnering with {OFFERING_LABELS[offering]}",
                      "body_blocks": body},
            "call_questions": [str(q)[:200] for q in (out.get("call_questions") or [])][:8]}


def _template(company, prop, offering, facts, ref, recipient) -> dict:
    by_field = {f["field"]: f for f in facts if f["kind"] == "fact"}
    desc = by_field.get("Description")
    loc = by_field.get("Local presence")
    greet = f"Dear {recipient['name'].split()[0]}," if recipient.get("name") else "Hello,"
    opening = (f" ahead of our opening on {prop.opening_date:%d %B %Y}" if prop.lifecycle == "pre_opening" and prop.opening_date else "")
    body = [{"text": greet, "claims": []},
            {"text": f"I lead corporate sales at {prop.name}{', ' + prop.locality if prop.locality else ''}{opening}.", "claims": []}]
    if loc:
        body.append({"text": f"Your team at {loc['value']} is close to us, which makes us a convenient option for visiting clients and colleagues.",
                     "claims": [ref[loc["id"]][0]]})
    elif desc:
        body.append({"text": f"I came across {company.name} and thought we might be useful to your team.", "claims": [ref[desc["id"]][0]]})
    body.append({"text": f"We'd like to offer {company.name} a {OFFERING_LABELS[offering].lower()} tailored to your needs.", "claims": []})
    body.append({"text": "Would you be open to a 15-minute call or a site visit next week?", "claims": []})
    return {"brief": {"summary": [{"text": f["field"] + ": " + f["value"], "claims": [ref[f["id"]][0]]} for f in facts if f["kind"] == "fact"][:4],
                      "opportunity": [], "recommended_offering": offering,
                      "approach": "AI drafting is off; this is a template. Personalise it before sending."},
            "email": {"subject": f"{prop.name} × {company.name}", "body_blocks": body},
            "call_questions": ["How often do clients or colleagues visit your office here?", "Where do they usually stay today?",
                               "Do you run offsites, trainings or events in the city?", "Who manages hotel bookings for your team?"]}
