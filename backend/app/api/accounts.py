"""Accounts (Company × Property): explorer list, detail, status changes, bulk, export, map, re-research."""
from __future__ import annotations

import base64
import csv
import io
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from geoalchemy2.shape import to_shape
from pydantic import BaseModel, Field
from sqlalchemy import and_, exists, func, or_, select

from app.api.deps import CtxDep
from app.api.lab import feedback_out
from app.api.serializers import (account_items, activity_out, claim_out, contact_out, iso, opportunity_out, point,
                                 role_label, signal_out, source_ref)
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.vocab import DISMISS_REASONS, INDUSTRIES
from app.models import (Account, AccountScore, ActivityRow, Claim, Company, CompanyLocation, Contact, CopilotOutput,
                        DiscoveryJob, DiscoveryResult, LeadFeedback, Membership, Opportunity, Property, Signal, SignalFeedback,
                        Source, TargetRoleRecommendation)
from app.workflow import engine
from app.workflow.engine import NewTask

router = APIRouter(tags=["accounts"])

SORTS = {"priority": Account.priority, "fit": Account.fit, "intent": Account.intent, "confidence": Account.confidence,
         "distance_km": Account.distance_km, "name": Company.name, "updated_at": Account.updated_at}
ORDER = ["discovered", "qualified", "contact_identified", "outreach_prepared", "outreach_sent", "engaged"]


def _filtered(ctx, property_id: UUID, q: str | None, status: str | None, tier: str | None, industry: str | None,
              distance_max_km: float | None, owner: str | None, min_fit: int | None, min_intent: int | None,
              has_signal: bool | None, job_id: UUID | None = None, ids: str | None = None):
    stmt = select(Account, Company).join(Company, Company.id == Account.company_id).where(Account.property_id == property_id)
    if job_id:
        stmt = stmt.where(exists().where(DiscoveryResult.job_id == job_id, DiscoveryResult.account_id == Account.id))
    if ids:
        try:
            stmt = stmt.where(Account.id.in_([UUID(x) for x in ids.split(",") if x.strip()][:1000]))
        except ValueError as e:
            raise ValidationFailed("ids must be a comma-separated list of account ids") from e
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Company.name.ilike(like), Company.primary_domain.ilike(like)))
    if status:
        vals = status.split(",")
        neg = [v[1:] for v in vals if v.startswith("!")]
        pos = [v for v in vals if not v.startswith("!")]
        if pos:
            stmt = stmt.where(Account.status.in_(pos))
        if neg:
            stmt = stmt.where(Account.status.not_in(neg))
    if tier:
        stmt = stmt.where(Account.tier.in_(tier.split(",")))
    if industry:
        stmt = stmt.where(Company.industry_code.in_(industry.split(",")))
    if distance_max_km is not None:
        stmt = stmt.where(Account.distance_km <= distance_max_km)
    if owner == "unassigned":
        stmt = stmt.where(Account.owner_membership_id.is_(None))
    elif owner == "me":
        stmt = stmt.where(Account.owner_membership_id == ctx.p.membership_id)
    elif owner:
        stmt = stmt.where(Account.owner_membership_id == UUID(owner))
    if min_fit is not None:
        stmt = stmt.where(Account.fit >= min_fit)
    if min_intent is not None:
        stmt = stmt.where(Account.intent >= min_intent)
    if has_signal:
        stmt = stmt.where(exists().where(Signal.company_id == Company.id))
    return stmt


@router.get("/properties/{property_id}/accounts")
def list_accounts(property_id: UUID, ctx: CtxDep, q: str | None = None, status: str | None = None, tier: str | None = None,
                  industry: str | None = None, distance_max_km: float | None = None, owner: str | None = None,
                  min_fit: int | None = None, min_intent: int | None = None, has_signal: bool | None = None,
                  sort: str = "-priority", limit: int = 50, cursor: str | None = None, job_id: UUID | None = None,
                  ids: str | None = None):
    ctx.property(property_id)
    stmt = _filtered(ctx, property_id, q, status, tier, industry, distance_max_km, owner, min_fit, min_intent, has_signal,
                     job_id, ids)
    total = ctx.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    desc = sort.startswith("-")
    col = SORTS.get(sort.lstrip("-"), Account.priority)
    stmt = stmt.order_by(col.desc().nullslast() if desc else col.asc().nullslast(), Company.name, Account.id)
    limit = max(1, min(200, limit))
    offset = int(base64.urlsafe_b64decode(cursor.encode()).decode()) if cursor else 0
    rows = ctx.db.execute(stmt.offset(offset).limit(limit)).all()
    nxt = offset + limit
    return {"items": account_items(ctx.db, [(a, c) for a, c in rows]),
            "next_cursor": base64.urlsafe_b64encode(str(nxt).encode()).decode() if nxt < total else None, "total": total}


@router.get("/properties/{property_id}/accounts/map")
def accounts_map(property_id: UUID, ctx: CtxDep):
    ctx.property(property_id)
    rows = ctx.db.execute(select(Account.id, Company.name, Account.tier, Account.status, CompanyLocation.location)
                          .join(Company, Company.id == Account.company_id)
                          .join(CompanyLocation, CompanyLocation.company_id == Company.id)
                          .where(Account.property_id == property_id, CompanyLocation.location.is_not(None))).all()
    seen, out = set(), []
    for aid, name, tier, status, loc in rows:
        if aid in seen:
            continue
        seen.add(aid)
        p = to_shape(loc)
        out.append({"id": str(aid), "name": name, "lat": p.y, "lng": p.x, "tier": tier, "status": status})
    return out


@router.get("/properties/{property_id}/accounts/export.csv")
def export_accounts(property_id: UUID, ctx: CtxDep, q: str | None = None, status: str | None = None, tier: str | None = None,
                    industry: str | None = None, distance_max_km: float | None = None, owner: str | None = None,
                    min_fit: int | None = None, min_intent: int | None = None, has_signal: bool | None = None,
                    job_id: UUID | None = None, ids: str | None = None):
    prop = ctx.property(property_id)
    stmt = _filtered(ctx, property_id, q, status, tier, industry, distance_max_km, owner, min_fit, min_intent, has_signal,
                     job_id, ids)
    rows = ctx.db.execute(stmt.order_by(Account.priority.desc().nullslast()).limit(10000)).all()
    items = account_items(ctx.db, [(a, c) for a, c in rows])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["company", "domain", "industry", "employees", "locality", "distance_km", "tier", "priority", "fit", "intent",
                "confidence", "top_signal", "signal_age_days", "status", "owner", "data_origin"])
    for it in items:
        c, s = it["company"], it["top_signal"]
        w.writerow([c["name"], c["domain"], c["industry_label"], c["employee_range"], c["locality"], it["distance_km"], it["tier"],
                    it["priority"], it["fit"], it["intent"], it["confidence"], s["title"] if s else "", s["age_days"] if s else "",
                    it["status"], it["owner"]["name"] if it["owner"] else "", c["data_origin"]])
    ctx.audit("accounts.export", "property", property_id, after={"rows": len(items)})
    fname = f"halo-accounts-{prop.name.lower().replace(' ', '-')[:40]}-{datetime.now(timezone.utc):%Y%m%d}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


class BulkIn(BaseModel):
    account_ids: list[UUID] = Field(min_length=1, max_length=500)
    action: str = Field(pattern="^(assign|set_status|dismiss)$")
    owner_membership_id: UUID | None = None
    status: str | None = None
    dismissed_reason: str | None = None
    dismissed_note: str | None = None


@router.post("/properties/{property_id}/accounts/bulk")
def bulk(property_id: UUID, body: BulkIn, ctx: CtxDep):
    ctx.property(property_id)
    accs = ctx.db.execute(select(Account).where(Account.property_id == property_id, Account.id.in_(body.account_ids))).scalars().all()
    for a in accs:
        _apply_patch(ctx, a, {"owner_membership_id": body.owner_membership_id} if body.action == "assign" else
                     {"status": "dismissed", "dismissed_reason": body.dismissed_reason, "dismissed_note": body.dismissed_note}
                     if body.action == "dismiss" else {"status": body.status})
    return {"updated": len(accs)}


class AccountPatch(BaseModel):
    model_config = {"extra": "ignore"}
    status: str | None = None
    owner_membership_id: UUID | None = None
    dismissed_reason: str | None = None
    dismissed_note: str | None = None


def log_activity(ctx, account: Account, type_: str, body: str, **meta) -> None:
    ctx.db.add(ActivityRow(workspace_id=ctx.p.workspace_id, account_id=account.id, type=type_, body=body,
                           actor_membership_id=ctx.p.membership_id, meta=meta))
    account.last_activity_at = datetime.now(timezone.utc)


def _apply_patch(ctx, a: Account, data: dict) -> None:
    if "owner_membership_id" in data:
        mid = data["owner_membership_id"]
        if mid and not ctx.db.execute(select(Membership).where(Membership.id == mid, Membership.workspace_id == ctx.p.workspace_id)).first():
            raise ValidationFailed("Unknown team member")
        if a.owner_membership_id != mid:
            a.owner_membership_id = mid
            who = ctx.db.execute(select(Membership).where(Membership.id == mid)).scalar_one_or_none() if mid else None
            log_activity(ctx, a, "system", "Owner changed" if mid else "Owner removed", owner=str(mid) if mid else None)
    st = data.get("status")
    if st and st != a.status:
        if st not in ORDER + ["dismissed"]:
            raise ValidationFailed("Unknown status")
        if st == "dismissed":
            reason = data.get("dismissed_reason")
            if reason not in DISMISS_REASONS:
                raise ValidationFailed("Choose a reason for dismissing this account.")
            a.dismissed_reason, a.dismissed_note = reason, data.get("dismissed_note")
        elif a.status == "dismissed":
            a.dismissed_reason, a.dismissed_note = None, None
        log_activity(ctx, a, "status_change", f"Status: {a.status.replace('_', ' ')} → {st.replace('_', ' ')}", **{"from": a.status, "to": st})
        a.status = st


def _account(ctx, account_id: UUID) -> Account:
    a = ctx.db.get(Account, account_id)
    if a is None:
        raise NotFound("Account not found")
    ctx.property(a.property_id)
    return a


def account_detail(ctx, a: Account) -> dict:
    db = ctx.db
    company = db.get(Company, a.company_id)
    prop = db.get(Property, a.property_id)
    base = account_items(db, [(a, company)])[0]
    loc = db.execute(select(CompanyLocation).where(CompanyLocation.company_id == company.id)).scalars().first()
    claims = db.execute(select(Claim, Source).outerjoin(Source, Source.id == Claim.source_id)
                        .where(Claim.company_id == company.id, Claim.is_current.is_(True))
                        .order_by(Claim.field, Claim.kind)).all()
    sigs = db.execute(select(Signal, Source).outerjoin(Source, Source.id == Signal.source_id)
                      .where(Signal.company_id == company.id).order_by(Signal.published_at.desc().nullslast())).all()
    sources = db.execute(select(Source).where(Source.company_id == company.id).order_by(Source.retrieved_at.desc()).limit(60)).scalars().all()
    score = db.get(AccountScore, a.current_score_id) if a.current_score_id else None
    roles = db.execute(select(TargetRoleRecommendation).where(TargetRoleRecommendation.account_id == a.id)
                       .order_by(TargetRoleRecommendation.rank)).scalars().all()
    contacts = db.execute(select(Contact).where(Contact.company_id == company.id, Contact.archived_at.is_(None))
                          .order_by(Contact.created_at)).scalars().all()
    opps = db.execute(select(Opportunity).where(Opportunity.account_id == a.id, Opportunity.archived_at.is_(None))
                      .order_by(Opportunity.created_at.desc())).scalars().all()
    acts = db.execute(select(ActivityRow).where(ActivityRow.account_id == a.id).order_by(ActivityRow.occurred_at.desc()).limit(100)).scalars().all()
    related = db.execute(select(Account, Property.name).join(Property, Property.id == Account.property_id)
                         .where(Account.company_id == company.id, Account.id != a.id)).all()
    has_draft = db.execute(select(func.count()).select_from(CopilotOutput).where(CopilotOutput.account_id == a.id)).scalar_one() > 0
    web = next((c for c, _ in claims if c.field == "website" and c.kind == "fact"), None)
    sig_fb = {sid: v for sid, v in db.execute(select(SignalFeedback.signal_id, SignalFeedback.verdict).where(
        SignalFeedback.signal_id.in_([s.id for s, _ in sigs]))).all()} if sigs else {}

    if company.research_status in ("not_researched", "failed"):
        na = {"kind": "research", "title": "Research this company",
              "detail": "We have map data only. Research the website and news to verify facts and find signals."}
    elif a.status == "dismissed":
        na = {"kind": "none", "title": f"Dismissed · {DISMISS_REASONS.get(a.dismissed_reason or '', 'no reason')}",
              "detail": "Dismiss reasons are used to improve scoring. Restore the account to work it again."}
    elif not contacts:
        r = roles[0] if roles else None
        lbl = role_label(r.role_code) if r else ""
        art = "an" if lbl[:1].upper() in "AEIOU" else "a"
        na = {"kind": "add_contact", "title": f"Find {art} {lbl} contact" if r else "Add a contact",
              "detail": "Roles to approach are identified, but no contact is on record. Add someone you know or found on the company's site."}
    elif a.status in ("discovered", "qualified", "contact_identified") and not has_draft:
        na = {"kind": "prepare_outreach", "title": "Prepare outreach",
              "detail": "Generate a brief and a first email grounded in the verified facts."}
    elif a.status == "outreach_prepared":
        na = {"kind": "prepare_outreach", "title": "Send the prepared outreach",
              "detail": "A draft is ready. Review it, send it from your mailbox and mark it as sent."}
    elif a.status == "outreach_sent":
        na = {"kind": "follow_up", "title": "Follow up", "detail": "Log the reply or schedule a follow-up call."}
    elif a.status == "engaged" and not opps:
        na = {"kind": "create_opportunity", "title": "Create an opportunity", "detail": "Track the deal value and stage."}
    else:
        na = {"kind": "none", "title": "Keep the opportunity moving", "detail": "Update the stage as the conversation progresses."}

    return {
        **base, "property_name": prop.name, "dismissed_reason": a.dismissed_reason, "dismissed_note": a.dismissed_note,
        "company": {**base["company"], "description": company.description, "hq_city": company.hq_city,
                    "address": loc.address if loc else None, "location": point(loc.location) if loc else None,
                    "website": company.website or (web.value if web else None), "research_status": company.research_status,
                    "last_researched_at": iso(company.last_researched_at), "do_not_contact": company.do_not_contact},
        "score": ({"fit": score.fit, "intent": score.intent, "confidence": score.confidence, "priority": score.priority,
                   "tier": score.tier, "actionability": score.actionability, "model_version": score.model_version,
                   "computed_at": iso(score.computed_at), "breakdown": score.breakdown} if score else None),
        "claims": [claim_out(c, s) for c, s in claims],
        "signals": [{**signal_out(s, src), "feedback": sig_fb.get(s.id)} for s, src in sigs],
        "feedback": feedback_out(db.execute(select(LeadFeedback).where(LeadFeedback.account_id == a.id)).scalar_one_or_none()),
        "sources": [source_ref(s) for s in sources],
        "roles": [{"role_code": r.role_code, "label": role_label(r.role_code), "offering": r.offering, "rank": r.rank,
                   "rationale": r.rationale} for r in roles],
        "contacts": [contact_out(c) for c in contacts],
        "opportunities": [opportunity_out(db, o, company.name) for o in opps],
        "activities": [activity_out(db, x) for x in acts],
        "related_accounts": [{"id": str(ra.id), "property_id": str(ra.property_id), "property_name": pn, "tier": ra.tier,
                              "status": ra.status} for ra, pn in related],
        "next_action": na,
    }


@router.get("/accounts/{account_id}")
def get_account(account_id: UUID, ctx: CtxDep):
    return account_detail(ctx, _account(ctx, account_id))


@router.patch("/accounts/{account_id}")
def patch_account(account_id: UUID, body: AccountPatch, ctx: CtxDep):
    a = _account(ctx, account_id)
    _apply_patch(ctx, a, body.model_dump(exclude_unset=True))
    ctx.db.flush()
    return account_detail(ctx, a)


@router.post("/accounts/{account_id}/research", status_code=202)
def research_account(account_id: UUID, ctx: CtxDep):
    a = _account(ctx, account_id)
    company = ctx.db.get(Company, a.company_id)
    running = ctx.db.execute(select(func.count()).select_from(DiscoveryJob).where(
        DiscoveryJob.property_id == a.property_id, DiscoveryJob.kind == "refresh",
        DiscoveryJob.status.in_(("queued", "running")), DiscoveryJob.config["account_id"].astext == str(a.id))).scalar_one()
    if running:
        raise Conflict("Research for this account is already running.")
    cfg = {"property_id": str(a.property_id), "radius_km": 15, "industries": [], "sources": [], "max_companies": 1,
           "research_depth": "standard", "signal_window_days": 365, "budget_usd": 1.0, "account_id": str(a.id)}
    j = DiscoveryJob(workspace_id=ctx.p.workspace_id, property_id=a.property_id, created_by=ctx.p.user_id, kind="refresh",
                     config=cfg, budget_usd=1.0)
    ctx.db.add(j)
    ctx.db.flush()
    engine.start_job(ctx.db, j, NewTask("research", subject_id=company.id, subject_label=company.name,
                                        input={"company_id": str(company.id), "account_id": str(a.id)}))
    log_activity(ctx, a, "system", "Research refresh started")
    return {"job_id": str(j.id)}
