"""Halo Lab (D-47): team ratings (the answer key), agent versions, improvement runs."""
from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, File, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import CtxDep
from app.api.serializers import iso
from app.core.errors import NotFound, ValidationFailed
from app.discovery.common import normalize_name
from app.lab import harness
from app.models import (Account, AgentVersion, Company, DiscoveryJob, LabLesson, LeadFeedback, Property, Signal,
                        SignalFeedback)
from app.providers.fetcher import registrable_domain

router = APIRouter(tags=["lab"])

# Why a prospect is not a fit. Shown as quick chips next to 👎.
NOT_FIT_REASONS = {
    "not_a_business": "Not a real business office",
    "wrong_industry": "Wrong industry for us",
    "too_small": "Too small",
    "too_far": "Too far away",
    "no_travel_need": "No reason to need a hotel",
    "other": "Other",
}
# Dismissals that say something about fit (others, like "duplicate" or "already a customer", don't).
DISMISS_AS_NOT_FIT = {"not_relevant_industry": "wrong_industry", "too_small": "too_small", "too_far": "too_far"}
MIN_RATINGS = 12          # below this an improvement round can't be judged fairly
RECOMMENDED_RATINGS = 30


class FeedbackIn(BaseModel):
    verdict: str = Field(pattern="^(good_fit|not_fit)$")
    reason: str | None = None
    note: str | None = Field(default=None, max_length=1000)


class SignalFeedbackIn(BaseModel):
    verdict: str = Field(pattern="^(correct|wrong)$")
    note: str | None = Field(default=None, max_length=1000)


def feedback_out(f: LeadFeedback | None) -> dict | None:
    if f is None:
        return None
    return {"verdict": f.verdict, "reason": f.reason, "reason_label": NOT_FIT_REASONS.get(f.reason or ""),
            "note": f.note, "source": f.source, "updated_at": iso(f.updated_at)}


def _account(ctx, account_id: UUID) -> Account:
    a = ctx.db.get(Account, account_id)
    if a is None:
        raise NotFound("Prospect not found")
    ctx.property(a.property_id)
    return a


def upsert_feedback(ctx, a: Account, verdict: str, reason: str | None, note: str | None, source: str = "app") -> tuple[LeadFeedback, bool]:
    if verdict == "good_fit":
        reason = None
    elif reason is not None and reason not in NOT_FIT_REASONS:
        raise ValidationFailed(f"Unknown reason. Use one of: {', '.join(NOT_FIT_REASONS)}")
    f = ctx.db.execute(select(LeadFeedback).where(LeadFeedback.account_id == a.id)).scalar_one_or_none()
    created = f is None
    if f is None:
        f = LeadFeedback(workspace_id=ctx.p.workspace_id, account_id=a.id, property_id=a.property_id, company_id=a.company_id,
                         verdict=verdict)
        ctx.db.add(f)
    f.verdict, f.reason, f.note, f.source = verdict, reason, (note or None), source
    f.created_by_membership_id = ctx.p.membership_id
    ctx.db.flush()
    return f, created


@router.put("/accounts/{account_id}/feedback")
def rate_prospect(account_id: UUID, body: FeedbackIn, ctx: CtxDep):
    a = _account(ctx, account_id)
    f, _ = upsert_feedback(ctx, a, body.verdict, body.reason, body.note)
    return feedback_out(f)


@router.delete("/accounts/{account_id}/feedback", status_code=204)
def clear_rating(account_id: UUID, ctx: CtxDep):
    a = _account(ctx, account_id)
    f = ctx.db.execute(select(LeadFeedback).where(LeadFeedback.account_id == a.id)).scalar_one_or_none()
    if f:
        ctx.db.delete(f)
    return Response(status_code=204)


def _signal(ctx, signal_id: UUID) -> Signal:
    s = ctx.db.get(Signal, signal_id)
    if s is None:
        raise NotFound("Signal not found")
    # Visible only if the caller can see a prospect for this company.
    pids = ctx.db.execute(select(Account.property_id).where(Account.company_id == s.company_id)).scalars().all()
    allowed = ctx.accessible_property_ids()
    if allowed is not None and not set(pids) & set(allowed):
        raise NotFound("Signal not found")
    return s


@router.put("/signals/{signal_id}/feedback")
def rate_signal(signal_id: UUID, body: SignalFeedbackIn, ctx: CtxDep):
    s = _signal(ctx, signal_id)
    f = ctx.db.execute(select(SignalFeedback).where(SignalFeedback.signal_id == s.id)).scalar_one_or_none()
    if f is None:
        f = SignalFeedback(workspace_id=ctx.p.workspace_id, signal_id=s.id, company_id=s.company_id, verdict=body.verdict)
        ctx.db.add(f)
    f.verdict, f.note, f.created_by_membership_id = body.verdict, body.note or None, ctx.p.membership_id
    ctx.db.flush()
    return {"signal_id": str(s.id), "verdict": f.verdict, "note": f.note}


@router.delete("/signals/{signal_id}/feedback", status_code=204)
def clear_signal_rating(signal_id: UUID, ctx: CtxDep):
    s = _signal(ctx, signal_id)
    f = ctx.db.execute(select(SignalFeedback).where(SignalFeedback.signal_id == s.id)).scalar_one_or_none()
    if f:
        ctx.db.delete(f)
    return Response(status_code=204)


# ───────── CSV ratings ─────────
GOOD = {"good", "good_fit", "good fit", "yes", "y", "1", "true", "fit", "hot", "warm", "👍"}
BAD = {"bad", "not_fit", "not fit", "no", "n", "0", "false", "not a fit", "cool", "cold", "👎"}
COLS = {"name": {"company", "company_name", "company name", "name", "account"},
        "website": {"website", "domain", "website_domain", "url", "site"},
        "verdict": {"verdict", "rating", "fit", "good_fit", "is_relevant_target", "good lead", "label"},
        "reason": {"reason"}, "note": {"note", "notes", "comment", "comments"}}


@router.post("/lab/ratings/import")
async def import_ratings(property_id: UUID, ctx: CtxDep, file: UploadFile = File(...)):
    ctx.require_role("admin", "manager")
    ctx.property(property_id)
    raw = await file.read()
    if len(raw) > 2_000_000:
        raise ValidationFailed("The file is larger than 2 MB")
    try:
        data = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        data = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(data))
    headers = reader.fieldnames or []
    col = {k: next((h for h in headers if h and h.strip().lower() in names), None) for k, names in COLS.items()}
    if not col["name"] or not col["verdict"]:
        raise ValidationFailed("The file needs a 'Company' column and a 'Verdict' column (good / not a fit).")
    rows = ctx.db.execute(select(Account, Company).join(Company, Company.id == Account.company_id)
                          .where(Account.property_id == property_id)).all()
    by_domain = {c.primary_domain: a for a, c in rows if c.primary_domain}
    by_name = {c.normalized_name: a for a, c in rows}
    created = updated = 0
    unmatched, invalid = [], []
    for i, r in enumerate(reader, start=2):
        if i > 2001:
            break
        name = (r.get(col["name"]) or "").strip()
        v = (r.get(col["verdict"]) or "").strip().lower()
        if not name:
            continue
        verdict = "good_fit" if v in GOOD else "not_fit" if v in BAD else None
        if verdict is None:
            invalid.append({"row": i, "company": name, "message": f"Verdict '{v}' isn't good / not a fit"})
            continue
        site = (r.get(col["website"]) or "").strip() if col["website"] else ""
        dom = registrable_domain(site if "://" in site else f"https://{site}") if site else None
        a = by_domain.get(dom) if dom else None
        a = a or by_name.get(normalize_name(name))
        if a is None:
            unmatched.append(name)
            continue
        reason = (r.get(col["reason"]) or "").strip().lower() if col["reason"] else None
        _, was_new = upsert_feedback(ctx, a, verdict, reason if reason in NOT_FIT_REASONS else None,
                                     (r.get(col["note"]) or "").strip() if col["note"] else None, source="csv")
        created += was_new
        updated += not was_new
    ctx.audit("lab.ratings_import", "property", property_id, after={"created": created, "updated": updated})
    return {"created": created, "updated": updated, "unmatched": unmatched[:50], "unmatched_count": len(unmatched),
            "invalid": invalid[:20]}


# ───────── summary & versions ─────────
def version_out(v: AgentVersion) -> dict:
    return {"id": str(v.id), "version": v.version, "status": v.status, "parent_version": v.parent_version,
            "summary": v.summary, "changes": v.changes or [], "metrics": v.metrics or {},
            "classify_guidance": (v.harness or {}).get("classify_guidance") or "",
            "lab_job_id": str(v.lab_job_id) if v.lab_job_id else None,
            "created_at": iso(v.created_at), "decided_at": iso(v.decided_at)}


def rating_counts(ctx) -> dict:
    db = ctx.db
    live = select(Property.id).where(Property.archived_at.is_(None))
    rows = db.execute(select(LeadFeedback.property_id, LeadFeedback.verdict, func.count())
                      .where(LeadFeedback.property_id.in_(live))
                      .group_by(LeadFeedback.property_id, LeadFeedback.verdict)).all()
    rated_ids = select(LeadFeedback.account_id)
    dismissed = db.execute(select(func.count()).select_from(Account).where(
        Account.status == "dismissed", Account.dismissed_reason.in_(list(DISMISS_AS_NOT_FIT)),
        Account.id.not_in(rated_ids), Account.property_id.in_(live))).scalar_one()
    names = dict(db.execute(select(Property.id, Property.name).where(Property.archived_at.is_(None))).all())
    per: dict = {}
    for pid, verdict, n in rows:
        d = per.setdefault(pid, {"property_id": str(pid), "property_name": names.get(pid, ""), "good_fit": 0, "not_fit": 0})
        d[verdict] += n
    good = sum(d["good_fit"] for d in per.values())
    bad = sum(d["not_fit"] for d in per.values()) + dismissed
    sig = dict(db.execute(select(SignalFeedback.verdict, func.count()).group_by(SignalFeedback.verdict)).all())
    return {"good_fit": good, "not_fit": bad, "total": good + bad, "from_dismissals": dismissed,
            "per_project": sorted(per.values(), key=lambda d: -(d["good_fit"] + d["not_fit"])),
            "signals_correct": sig.get("correct", 0), "signals_wrong": sig.get("wrong", 0)}


@router.get("/lab/summary")
def lab_summary(ctx: CtxDep):
    db = ctx.db
    active = harness.active_version(db, ctx.p.workspace_id)
    counts = rating_counts(ctx)
    cand = db.execute(select(AgentVersion).where(AgentVersion.status == "candidate")
                      .order_by(AgentVersion.version.desc())).scalars().first()
    job = db.execute(select(DiscoveryJob).where(DiscoveryJob.kind == "lab")
                     .order_by(DiscoveryJob.created_at.desc())).scalars().first()
    lessons = db.execute(select(LabLesson).where(LabLesson.is_active.is_(True))
                         .order_by(LabLesson.created_at.desc()).limit(8)).scalars().all()
    has_both = counts["good_fit"] >= 3 and counts["not_fit"] >= 3
    return {
        "active_version": version_out(active),
        "candidate": version_out(cand) if cand else None,
        "ratings": counts,
        "min_ratings": MIN_RATINGS, "recommended_ratings": RECOMMENDED_RATINGS,
        "ready": counts["total"] >= MIN_RATINGS and has_both,
        "not_ready_reason": (None if counts["total"] >= MIN_RATINGS and has_both else
                             f"Rate at least {MIN_RATINGS} prospects, including at least 3 good fits and 3 that aren't."),
        "last_run": ({"job_id": str(job.id), "status": job.status, "property_id": str(job.property_id),
                      "created_at": iso(job.created_at), "finished_at": iso(job.finished_at), "error": job.error}
                     if job else None),
        "lessons": [{"id": str(x.id), "text": x.text, "evidence": x.evidence, "created_at": iso(x.created_at)} for x in lessons],
        "not_fit_reasons": NOT_FIT_REASONS,
        "can_manage": ctx.p.role in ("admin", "manager"),
    }


@router.get("/lab/versions")
def list_versions(ctx: CtxDep):
    harness.active_version(ctx.db, ctx.p.workspace_id)
    vs = ctx.db.execute(select(AgentVersion).order_by(AgentVersion.version.desc()).limit(50)).scalars().all()
    return [version_out(v) for v in vs]
