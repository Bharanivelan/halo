"""Contacts, copilot drafts, opportunities, activities, and activity/usage views."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.api.accounts import _account, _apply_patch, log_activity
from app.api.deps import CtxDep
from app.api.discovery import job_summary
from app.api.serializers import activity_out, contact_out, iso, opportunity_out
from app.copilot import service as copilot
from app.core.errors import NotFound, ValidationFailed
from app.core.regions import region
from app.core.vocab import LOSS_REASONS, OFFERING_LABELS, ROLE_CODES, Offering
from app.models import (Account, ActivityRow, Company, Contact, CopilotOutput, DiscoveryJob, LlmCall, Opportunity,
                        ProviderCall)
from app.scoring.engine import ROLE_WHY  # noqa: F401  (kept for future contact suggestions)
from app.discovery.steps import compute_and_store_score

router = APIRouter(tags=["engagement"])


# ───────── contacts ─────────
class ContactIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    title: str | None = None
    role_code: str | None = None
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=40)
    profile_url: str | None = None
    source_note: str = Field(min_length=3, max_length=500)


class ContactPatch(BaseModel):
    model_config = {"extra": "ignore"}
    full_name: str | None = None
    title: str | None = None
    role_code: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    profile_url: str | None = None
    source_note: str | None = None
    do_not_contact: bool | None = None
    verification_status: str | None = Field(None, pattern="^(unverified|user_verified)$")


def _company(ctx, company_id: UUID) -> Company:
    c = ctx.db.get(Company, company_id)
    if c is None:
        raise NotFound("Company not found")
    # must be reachable through at least one accessible property
    ids = ctx.accessible_property_ids()
    q = select(Account.id).where(Account.company_id == c.id)
    if ids is not None:
        q = q.where(Account.property_id.in_(ids))
    if not ctx.db.execute(q).first():
        raise NotFound("Company not found")
    return c


def _rescore(ctx, company_id: UUID) -> None:
    for a in ctx.db.execute(select(Account).where(Account.company_id == company_id)).scalars():
        if a.current_score_id:
            compute_and_store_score(ctx.db, ctx.p.workspace_id, a)


@router.get("/properties/{property_id}/contacts")
def list_contacts(property_id: UUID, ctx: CtxDep, q: str | None = None):
    ctx.property(property_id)
    stmt = (select(Contact, Company.name, Account.id).join(Company, Company.id == Contact.company_id)
            .join(Account, (Account.company_id == Company.id) & (Account.property_id == property_id))
            .where(Contact.archived_at.is_(None)).order_by(Company.name, Contact.full_name))
    if q:
        stmt = stmt.where(Contact.full_name.ilike(f"%{q}%") | Company.name.ilike(f"%{q}%") | Contact.title.ilike(f"%{q}%"))
    return [contact_out(c, n, aid) for c, n, aid in ctx.db.execute(stmt).all()]


@router.post("/companies/{company_id}/contacts", status_code=201)
def create_contact(company_id: UUID, body: ContactIn, ctx: CtxDep):
    comp = _company(ctx, company_id)
    if body.role_code and body.role_code not in ROLE_CODES:
        raise ValidationFailed("Unknown role")
    c = Contact(workspace_id=ctx.p.workspace_id, company_id=comp.id, created_by=ctx.p.user_id, **body.model_dump())
    ctx.db.add(c)
    ctx.db.flush()
    for a in ctx.db.execute(select(Account).where(Account.company_id == comp.id)).scalars():
        if a.status in ("discovered", "qualified"):
            _apply_patch(ctx, a, {"status": "contact_identified"})
        log_activity(ctx, a, "system", f"Contact added: {c.full_name}{' · ' + c.title if c.title else ''}")
    _rescore(ctx, comp.id)
    return contact_out(c)


@router.patch("/contacts/{contact_id}")
def patch_contact(contact_id: UUID, body: ContactPatch, ctx: CtxDep):
    c = ctx.db.get(Contact, contact_id)
    if c is None:
        raise NotFound("Contact not found")
    _company(ctx, c.company_id)
    data = body.model_dump(exclude_unset=True)
    if "do_not_contact" in data and data["do_not_contact"] != c.do_not_contact:
        ctx.audit("contact.do_not_contact", "contact", c.id, before={"dnc": c.do_not_contact}, after={"dnc": data["do_not_contact"]})
    for k, v in data.items():
        setattr(c, k, v)
    ctx.db.flush()
    _rescore(ctx, c.company_id)
    return contact_out(c)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: UUID, ctx: CtxDep):
    c = ctx.db.get(Contact, contact_id)
    if c is None:
        raise NotFound("Contact not found")
    _company(ctx, c.company_id)
    c.archived_at = datetime.now(timezone.utc)
    ctx.audit("contact.delete", "contact", c.id)
    ctx.db.flush()
    _rescore(ctx, c.company_id)
    return Response(status_code=204)


class CompanyPatch(BaseModel):
    do_not_contact: bool


@router.patch("/companies/{company_id}")
def patch_company(company_id: UUID, body: CompanyPatch, ctx: CtxDep):
    c = _company(ctx, company_id)
    ctx.audit("company.do_not_contact", "company", c.id, before={"dnc": c.do_not_contact}, after={"dnc": body.do_not_contact})
    c.do_not_contact = body.do_not_contact
    return {"id": str(c.id), "do_not_contact": c.do_not_contact}


# ───────── copilot ─────────
class CopilotIn(BaseModel):
    offering: Offering
    contact_id: UUID | None = None
    role_code: str | None = None
    tone: str = Field("warm", pattern="^(warm|formal)$")


class DraftEdit(BaseModel):
    subject: str = Field(max_length=200)
    body: str = Field(max_length=10000)


def copilot_out(o: CopilotOutput) -> dict:
    return {"id": str(o.id), "account_id": str(o.account_id), "contact_id": str(o.contact_id) if o.contact_id else None,
            "offering": o.offering, "version": o.version, "status": o.status, "content": o.content, "edited": o.edited,
            "generated_by": o.generated_by, "created_at": iso(o.created_at)}


@router.post("/accounts/{account_id}/copilot")
def generate_copilot(account_id: UUID, body: CopilotIn, ctx: CtxDep):
    a = _account(ctx, account_id)
    out = copilot.generate(ctx.db, workspace_id=ctx.p.workspace_id, user_id=ctx.p.user_id, account=a, offering=str(body.offering),
                           contact_id=body.contact_id, role_code=body.role_code, tone=body.tone)
    ctx.db.flush()
    if a.status in ("discovered", "qualified", "contact_identified"):
        _apply_patch(ctx, a, {"status": "outreach_prepared"})
    log_activity(ctx, a, "system", f"Outreach draft v{out.version} generated ({OFFERING_LABELS[out.offering]})")
    return copilot_out(out)


@router.get("/accounts/{account_id}/copilot")
def list_copilot(account_id: UUID, ctx: CtxDep):
    a = _account(ctx, account_id)
    rows = ctx.db.execute(select(CopilotOutput).where(CopilotOutput.account_id == a.id).order_by(CopilotOutput.version.desc())).scalars()
    return [copilot_out(o) for o in rows]


def _draft(ctx, output_id: UUID) -> tuple[CopilotOutput, Account]:
    o = ctx.db.get(CopilotOutput, output_id)
    if o is None:
        raise NotFound("Draft not found")
    return o, _account(ctx, o.account_id)


@router.patch("/copilot-outputs/{output_id}")
def edit_draft(output_id: UUID, body: DraftEdit, ctx: CtxDep):
    o, _ = _draft(ctx, output_id)
    o.edited = body.model_dump()
    if o.status == "generated":
        o.status = "edited"
    return copilot_out(o)


@router.post("/copilot-outputs/{output_id}/copied")
def draft_copied(output_id: UUID, ctx: CtxDep):
    o, a = _draft(ctx, output_id)
    if o.status in ("generated", "edited"):
        o.status = "copied"
    log_activity(ctx, a, "draft_copied", f"Draft v{o.version} copied")
    return copilot_out(o)


@router.post("/copilot-outputs/{output_id}/mark-sent")
def draft_sent(output_id: UUID, ctx: CtxDep):
    o, a = _draft(ctx, output_id)
    o.status = "marked_sent"
    subject = (o.edited or {}).get("subject") or o.content.get("email", {}).get("subject")
    ctx.db.add(ActivityRow(workspace_id=ctx.p.workspace_id, account_id=a.id, contact_id=o.contact_id, type="email_sent",
                           body=f"Email sent: {subject}", actor_membership_id=ctx.p.membership_id, meta={"draft_id": str(o.id)}))
    if a.status in ("discovered", "qualified", "contact_identified", "outreach_prepared"):
        _apply_patch(ctx, a, {"status": "outreach_sent"})
    a.last_activity_at = datetime.now(timezone.utc)
    return copilot_out(o)


# ───────── opportunities & activities ─────────
class OpportunityIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    offering: Offering
    value_amount: float | None = Field(None, ge=0)
    expected_close_date: date | None = None
    probability: int | None = Field(None, ge=0, le=100)
    owner_membership_id: UUID | None = None


class OpportunityPatch(BaseModel):
    model_config = {"extra": "ignore"}
    name: str | None = None
    offering: Offering | None = None
    value_amount: float | None = None
    expected_close_date: date | None = None
    probability: int | None = Field(None, ge=0, le=100)
    owner_membership_id: UUID | None = None
    stage: str | None = Field(None, pattern="^(interested|meeting_scheduled|negotiation|won|lost)$")
    loss_reason: str | None = None
    loss_note: str | None = None


@router.get("/properties/{property_id}/opportunities")
def list_opps(property_id: UUID, ctx: CtxDep):
    ctx.property(property_id)
    rows = ctx.db.execute(select(Opportunity, Company.name).join(Account, Account.id == Opportunity.account_id)
                          .join(Company, Company.id == Account.company_id)
                          .where(Account.property_id == property_id, Opportunity.archived_at.is_(None))
                          .order_by(Opportunity.updated_at.desc())).all()
    return [opportunity_out(ctx.db, o, n) for o, n in rows]


@router.post("/accounts/{account_id}/opportunities", status_code=201)
def create_opp(account_id: UUID, body: OpportunityIn, ctx: CtxDep):
    a = _account(ctx, account_id)
    o = Opportunity(workspace_id=ctx.p.workspace_id, account_id=a.id, name=body.name, offering=str(body.offering),
                    value_amount=body.value_amount, expected_close_date=body.expected_close_date, probability=body.probability,
                    owner_membership_id=body.owner_membership_id or a.owner_membership_id or ctx.p.membership_id,
                    currency=region(ctx.property(a.property_id).country)["currency"])
    ctx.db.add(o)
    ctx.db.flush()
    if a.status != "engaged":
        _apply_patch(ctx, a, {"status": "engaged"})
    log_activity(ctx, a, "stage_change", f"Opportunity created: {o.name}")
    return opportunity_out(ctx.db, o)


@router.patch("/opportunities/{opp_id}")
def patch_opp(opp_id: UUID, body: OpportunityPatch, ctx: CtxDep):
    o = ctx.db.get(Opportunity, opp_id)
    if o is None:
        raise NotFound("Opportunity not found")
    a = _account(ctx, o.account_id)
    data = body.model_dump(exclude_unset=True)
    stage = data.pop("stage", None)
    if stage == "lost":
        reason = data.get("loss_reason") or o.loss_reason
        if reason not in LOSS_REASONS:
            raise ValidationFailed("Choose a loss reason before marking the opportunity as lost.")
    for k, v in data.items():
        setattr(o, k, str(v) if k == "offering" and v is not None else v)
    if stage and stage != o.stage:
        now = datetime.now(timezone.utc)
        log_activity(ctx, a, "stage_change", f"{o.name}: {o.stage.replace('_', ' ')} → {stage.replace('_', ' ')}",
                     opportunity=str(o.id))
        o.stage = stage
        o.won_at = now if stage == "won" else None
        o.lost_at = now if stage == "lost" else None
    ctx.db.flush()
    return opportunity_out(ctx.db, o)


class ActivityIn(BaseModel):
    type: str = Field(pattern="^(note|call|meeting|email_sent)$")
    body: str = Field(min_length=1, max_length=5000)
    opportunity_id: UUID | None = None


@router.get("/accounts/{account_id}/activities")
def list_activities(account_id: UUID, ctx: CtxDep):
    a = _account(ctx, account_id)
    rows = ctx.db.execute(select(ActivityRow).where(ActivityRow.account_id == a.id).order_by(ActivityRow.occurred_at.desc()).limit(200)).scalars()
    return [activity_out(ctx.db, x) for x in rows]


@router.post("/accounts/{account_id}/activities", status_code=201)
def add_activity(account_id: UUID, body: ActivityIn, ctx: CtxDep):
    a = _account(ctx, account_id)
    x = ActivityRow(workspace_id=ctx.p.workspace_id, account_id=a.id, opportunity_id=body.opportunity_id, type=body.type,
                    body=body.body, actor_membership_id=ctx.p.membership_id)
    ctx.db.add(x)
    a.last_activity_at = datetime.now(timezone.utc)
    ctx.db.flush()
    return activity_out(ctx.db, x)


# ───────── activity & usage ─────────
@router.get("/activity/jobs")
def activity_jobs(ctx: CtxDep):
    q = select(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()).limit(100)
    ids = ctx.accessible_property_ids()
    if ids is not None:
        q = q.where(DiscoveryJob.property_id.in_(ids))
    return [job_summary(ctx.db, j) for j in ctx.db.execute(q).scalars()]


@router.get("/activity/usage")
def usage(ctx: CtxDep, group_by: str = "step", days: int = 30):
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(365, days)))
    col = {"step": LlmCall.step, "model": LlmCall.model, "job": LlmCall.job_id}.get(group_by, LlmCall.step)
    rows = ctx.db.execute(select(col, func.count(), func.sum(LlmCall.input_tokens), func.sum(LlmCall.output_tokens),
                                 func.sum(LlmCall.cost_usd)).where(LlmCall.created_at >= since).group_by(col)
                          .order_by(func.sum(LlmCall.cost_usd).desc())).all()
    out = [{"key": str(k) if k else "—", "label": str(k) if k else "Interactive (no job)", "calls": n, "input_tokens": int(i or 0),
            "output_tokens": int(o or 0), "cost_usd": round(float(c or 0), 5)} for k, n, i, o, c in rows]
    prov = ctx.db.execute(select(ProviderCall.provider, func.count(), func.sum(ProviderCall.cost_usd))
                          .where(ProviderCall.created_at >= since).group_by(ProviderCall.provider)).all()
    if group_by == "step":
        out += [{"key": f"provider:{p}", "label": f"Data provider · {p}", "calls": n, "input_tokens": 0, "output_tokens": 0,
                 "cost_usd": round(float(c or 0), 5)} for p, n, c in prov]
    return out


@router.get("/activity/llm-calls")
def llm_calls(ctx: CtxDep, job_id: UUID | None = None):
    q = select(LlmCall).order_by(LlmCall.created_at.desc()).limit(300)
    if job_id:
        q = q.where(LlmCall.job_id == job_id)
    return [{"id": str(c.id), "step": c.step, "model": c.model, "prompt_id": c.prompt_id, "prompt_version": c.prompt_version,
             "input_tokens": c.input_tokens, "output_tokens": c.output_tokens, "cost_usd": float(c.cost_usd),
             "latency_ms": c.latency_ms, "status": c.status, "error": c.error, "created_at": iso(c.created_at)}
            for c in ctx.db.execute(q).scalars()]
