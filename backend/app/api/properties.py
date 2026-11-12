"""Reference data, members, geocoding, properties, overview, CSV imports."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select

from app.api.deps import CtxDep
from app.api.serializers import (account_items, iso, property_full, property_summary, signal_out)
from app.core.config import get_settings
from app.core.errors import ValidationFailed
from app.core.regions import DEFAULT_COUNTRY, REGIONS, region
from app.core.vocab import (ACCOUNT_STATUS_LABELS, DISMISS_REASONS, INDUSTRIES, LOSS_REASONS, OFFERING_LABELS, ROLE_CODES,
                            SIGNAL_TYPES, STAGE_LABELS, Offering)
from app.discovery.common import point_wkt
from app.models import (Account, Company, CsvImport, DiscoveryJob, LlmCall, Membership, Opportunity, Property,
                        PropertyOffering, PropertyTargetProfile, ScoringModel, Signal, Source, User)
from app.providers import geocoder

router = APIRouter(tags=["properties"])


@router.get("/reference")
def reference(ctx: CtxDep):
    s = get_settings()
    model = ctx.db.execute(select(ScoringModel).where(ScoringModel.is_active.is_(True)).order_by(ScoringModel.version.desc())).scalars().first()
    params = model.params if model else {}
    return {
        "industries": [{"code": k, "label": v[0]} for k, v in INDUSTRIES.items()],
        "offerings": [{"code": k, "label": v} for k, v in OFFERING_LABELS.items()],
        "account_statuses": [{"code": k, "label": v} for k, v in ACCOUNT_STATUS_LABELS.items()],
        "opportunity_stages": [{"code": k, "label": v} for k, v in STAGE_LABELS.items()],
        "dismiss_reasons": [{"code": k, "label": v} for k, v in DISMISS_REASONS.items()],
        "loss_reasons": [{"code": k, "label": v} for k, v in LOSS_REASONS.items()],
        "signal_types": [{"code": k, "label": v[0]} for k, v in SIGNAL_TYPES.items()],
        "role_codes": [{"code": k, "label": v} for k, v in ROLE_CODES.items()],
        "providers": [
            {"key": "osm", "label": "OpenStreetMap", "enabled": True},
            {"key": "csv", "label": "CSV import", "enabled": True},
            {"key": "web_search", "label": "Web search (Tavily)", "enabled": s.search_configured,
             "reason": None if s.search_configured else "Add TAVILY_API_KEY to the server .env to enable"},
            {"key": "google_places", "label": "Google Places", "enabled": False, "reason": "Optional, disabled by default (P-06)"},
        ],
        "regions": list(REGIONS.values()), "default_country": DEFAULT_COUNTRY,
        "llm_configured": s.llm_configured, "search_configured": s.search_configured,
        "scoring": {"tier_a_min": params.get("tiers", {}).get("A", 65), "tier_b_min": params.get("tiers", {}).get("B", 45),
                    "signal_window_days": params.get("signal_window_days", 365), "fresh_days": params.get("fresh_days", 90)},
    }


@router.get("/members")
def members(ctx: CtxDep):
    rows = ctx.db.execute(select(Membership.id, User.full_name, User.email, Membership.role).join(User, User.id == Membership.user_id)
                          .where(Membership.workspace_id == ctx.p.workspace_id, Membership.is_active.is_(True))
                          .order_by(User.full_name)).all()
    return [{"id": str(r[0]), "full_name": r[1], "email": r[2], "role": r[3]} for r in rows]


@router.get("/geocode")
def geocode(q: str, ctx: CtxDep, country: str | None = None):
    """Address search. `country` (any ISO code) keeps results inside the project's market."""
    if len(q.strip()) < 3:
        return []
    cc = country.upper() if country and country.upper() in REGIONS else None
    return list(geocoder.geocode(q.strip(), country=cc))


# ───────── properties ─────────
class GeoIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TargetIn(BaseModel):
    radius_km: float = Field(8.0, ge=1, le=50)
    industries: list[str] = []
    employee_min: int | None = None
    employee_max: int | None = None
    notes: str | None = None

    @field_validator("industries")
    @classmethod
    def known(cls, v):
        bad = [x for x in v if x not in INDUSTRIES]
        if bad:
            raise ValueError(f"Unknown industries: {', '.join(bad)}")
        return v


class PropertyIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    brand: str | None = None
    address_line: str | None = None
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = DEFAULT_COUNTRY
    location: GeoIn
    lifecycle: str = Field("pre_opening", pattern="^(pre_opening|operating)$")
    opening_date: date | None = None
    rooms_count: int | None = Field(None, ge=0)
    meeting_rooms_count: int | None = Field(None, ge=0)
    largest_meeting_capacity: int | None = Field(None, ge=0)
    banquet_capacity: int | None = Field(None, ge=0)
    restaurants_count: int | None = Field(None, ge=0)
    facilities: list[str] = []
    description: str | None = None
    is_hypothetical: bool = False
    offerings: list[Offering] = [Offering.corporate_rate]
    target: TargetIn = TargetIn()
    start_agent: bool = False  # D-40: create the project and kick off the first discovery run in one step

    @field_validator("country")
    @classmethod
    def supported_country(cls, v):
        v = v.upper()
        if v not in REGIONS:
            raise ValueError("Unknown country. Use a two-letter country code, e.g. US, IN, GB")
        return v


class PropertyPatch(BaseModel):
    model_config = {"extra": "ignore"}
    name: str | None = None
    brand: str | None = None
    address_line: str | None = None
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    location: GeoIn | None = None
    lifecycle: str | None = Field(None, pattern="^(pre_opening|operating)$")
    opening_date: date | None = None
    rooms_count: int | None = None
    meeting_rooms_count: int | None = None
    largest_meeting_capacity: int | None = None
    banquet_capacity: int | None = None
    restaurants_count: int | None = None
    facilities: list[str] | None = None
    description: str | None = None
    is_hypothetical: bool | None = None
    offerings: list[Offering] | None = None
    target: TargetIn | None = None


SIMPLE = ["name", "brand", "address_line", "locality", "city", "state", "postal_code", "country", "lifecycle", "opening_date",
          "rooms_count", "meeting_rooms_count", "largest_meeting_capacity", "banquet_capacity", "restaurants_count",
          "facilities", "description", "is_hypothetical"]


def _apply(ctx, prop: Property, data: dict) -> None:
    for k in SIMPLE:
        if k in data:
            setattr(prop, k, data[k])
    if data.get("location"):
        prop.location = point_wkt(data["location"]["lat"], data["location"]["lng"])
    if data.get("offerings") is not None:
        ctx.db.execute(delete(PropertyOffering).where(PropertyOffering.property_id == prop.id))
        for o in dict.fromkeys(data["offerings"]):
            ctx.db.add(PropertyOffering(workspace_id=ctx.p.workspace_id, property_id=prop.id, offering=str(o)))
    if data.get("target") is not None:
        t = ctx.db.execute(select(PropertyTargetProfile).where(PropertyTargetProfile.property_id == prop.id)).scalar_one_or_none()
        if t is None:
            t = PropertyTargetProfile(workspace_id=ctx.p.workspace_id, property_id=prop.id)
            ctx.db.add(t)
        for k, v in data["target"].items():
            setattr(t, k, v)


@router.get("/properties")
def list_properties(ctx: CtxDep):
    q = select(Property).where(Property.archived_at.is_(None)).order_by(Property.created_at)
    ids = ctx.accessible_property_ids()
    if ids is not None:
        q = q.where(Property.id.in_(ids))
    return [property_summary(ctx.db, p) for p in ctx.db.execute(q).scalars()]


@router.post("/properties", status_code=201)
def create_property(body: PropertyIn, ctx: CtxDep):
    ctx.require_role("admin", "manager")
    prop = Property(workspace_id=ctx.p.workspace_id, name=body.name)
    ctx.db.add(prop)
    ctx.db.flush()
    _apply(ctx, prop, body.model_dump(mode="python", exclude={"start_agent"}))
    ctx.db.flush()
    ctx.audit("property.create", "property", prop.id, after={"name": prop.name})
    out = property_full(ctx.db, prop)
    if body.start_agent:
        from app.api.discovery import autostart_config, start_discovery
        out["started_job_id"] = start_discovery(ctx, autostart_config(ctx, prop), "Automatic first run for a new project")["job_id"]
    return out


@router.get("/properties/{property_id}")
def get_property(property_id: UUID, ctx: CtxDep):
    return property_full(ctx.db, ctx.property(property_id))


@router.patch("/properties/{property_id}")
def patch_property(property_id: UUID, body: PropertyPatch, ctx: CtxDep):
    ctx.require_role("admin", "manager")
    prop = ctx.property(property_id)
    data = body.model_dump(mode="python", exclude_unset=True)
    if data.get("country") is not None:
        data["country"] = data["country"].upper()
        if data["country"] not in REGIONS:
            raise ValidationFailed("Unknown country. Use a two-letter country code, e.g. US, IN, GB")
    _apply(ctx, prop, data)
    ctx.db.flush()
    return property_full(ctx.db, prop)


@router.delete("/properties/{property_id}", status_code=204)
def archive_property(property_id: UUID, ctx: CtxDep):
    """Delete a project (D-38). Soft delete: it disappears everywhere, running agent work is stopped,
    and the rows stay recoverable by an admin. Admins and managers only."""
    ctx.require_role("admin", "manager")
    prop = ctx.property(property_id)
    from app.models import JobEvent, WorkflowTask
    now = datetime.now(timezone.utc)
    for j in ctx.db.execute(select(DiscoveryJob).where(DiscoveryJob.property_id == prop.id,
                                                       DiscoveryJob.status.in_(("queued", "running", "paused_budget", "cancelling")))).scalars():
        j.cancel_requested = True
        j.status = "cancelled"
        j.finished_at = now
        for t in ctx.db.execute(select(WorkflowTask).where(WorkflowTask.job_id == j.id,
                                                           WorkflowTask.status.in_(("pending", "blocked_budget")))).scalars():
            t.status = "skipped"
        ctx.db.add(JobEvent(workspace_id=j.workspace_id, job_id=j.id, level="warning", stage=None,
                            message=f"Stopped because the project was deleted by {ctx.p.full_name}."))
    prop.archived_at = now
    ctx.audit("property.archive", "property", prop.id, before={"name": prop.name})


@router.get("/properties/{property_id}/overview")
def overview(property_id: UUID, ctx: CtxDep):
    db = ctx.db
    prop = ctx.property(property_id)
    status_rows = db.execute(select(Account.status, func.count()).where(Account.property_id == prop.id).group_by(Account.status)).all()
    funnel = {k: 0 for k in ACCOUNT_STATUS_LABELS}
    for st, n in status_rows:
        funnel[st] = n
    tiers = {"A": 0, "B": 0, "C": 0}
    for t, n in db.execute(select(Account.tier, func.count()).where(Account.property_id == prop.id, Account.status != "dismissed",
                                                                    Account.tier.is_not(None)).group_by(Account.tier)).all():
        tiers[t] = n
    opp = {k: 0 for k in STAGE_LABELS}
    open_value = 0.0
    for o in db.execute(select(Opportunity).join(Account, Account.id == Opportunity.account_id)
                        .where(Account.property_id == prop.id, Opportunity.archived_at.is_(None))).scalars():
        opp[o.stage] += 1
        if o.stage not in ("won", "lost") and o.value_amount:
            open_value += float(o.value_amount)
    since = datetime.now(timezone.utc) - timedelta(days=45)
    sig_rows = db.execute(select(Signal, Source, Account.id, Company.name).join(Account, Account.company_id == Signal.company_id)
                          .join(Company, Company.id == Signal.company_id).outerjoin(Source, Source.id == Signal.source_id)
                          .where(Account.property_id == prop.id, Account.status != "dismissed",
                                 func.coalesce(Signal.published_at, Signal.discovered_at) >= since)
                          .order_by(func.coalesce(Signal.published_at, Signal.discovered_at).desc()).limit(8)).all()
    recent = [{**signal_out(s, src), "account_id": str(aid), "company_name": name} for s, src, aid, name in sig_rows]
    att = db.execute(select(Account, Company).join(Company, Company.id == Account.company_id)
                     .where(Account.property_id == prop.id, Account.status.in_(("discovered", "qualified", "outreach_prepared")),
                            Account.tier.in_(("A", "B")))
                     .order_by(Account.tier, Account.priority.desc().nullslast()).limit(5)).all()
    jobs = db.execute(select(DiscoveryJob).where(DiscoveryJob.property_id == prop.id,
                                                 DiscoveryJob.status.in_(("queued", "running", "paused_budget", "cancelling")))
                      .order_by(DiscoveryJob.created_at.desc())).scalars().all()
    from app.api.discovery import job_summary
    usage = db.execute(select(func.coalesce(func.sum(LlmCall.cost_usd), 0), func.count())
                       .where(LlmCall.created_at >= datetime.now(timezone.utc) - timedelta(days=30))).first()
    return {"property": property_summary(db, prop), "account_count": sum(funnel.values()), "tier_counts": tiers,
            "funnel": funnel, "opportunities": {**opp, "open_value": open_value, "currency": region(prop.country)["currency"]},
            "recent_signals": recent, "attention": account_items(db, att), "running_jobs": [job_summary(db, j) for j in jobs],
            "usage_30d": {"cost_usd": float(usage[0] or 0), "llm_calls": int(usage[1] or 0)}}


# ───────── CSV import ─────────
HEADER_MAP = {
    "name": ("name", "company", "company name", "company_name", "organisation", "organization", "account", "account name"),
    "website": ("website", "domain", "url", "web", "site", "company website"),
    "address": ("address", "office address", "location", "street"),
    "city": ("city", "town"),
    "notes": ("notes", "note", "comments", "comment"),
    "lat": ("lat", "latitude"),
    "lng": ("lng", "lon", "long", "longitude"),
}


@router.post("/properties/{property_id}/imports", status_code=201)
async def import_csv(property_id: UUID, ctx: CtxDep, file: UploadFile = File(...)):
    ctx.property(property_id)
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise ValidationFailed("CSV file is larger than 5 MB")
    try:
        text_data = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_data = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text_data))
    headers = reader.fieldnames or []
    mapping: dict[str, str | None] = {}
    for field, names in HEADER_MAP.items():
        mapping[field] = next((h for h in headers if h and h.strip().lower() in names), None)
    if not mapping["name"]:
        raise ValidationFailed("Couldn't find a company name column. Name it 'Company' or 'Name'.")
    rows, errors = [], []
    for i, r in enumerate(reader, start=2):
        if i > 5001:
            errors.append({"row": i, "message": "Only the first 5,000 rows are imported"})
            break
        row = {f: (r.get(h) or "").strip() for f, h in mapping.items() if h}
        if not row.get("name"):
            errors.append({"row": i, "message": "Missing company name"})
            continue
        rows.append(row)
    imp = CsvImport(workspace_id=ctx.p.workspace_id, property_id=property_id, file_name=(file.filename or "import.csv")[:300],
                    status="parsed" if rows else "failed", mapping=mapping, rows=rows, errors=errors, created_by=ctx.p.user_id)
    ctx.db.add(imp)
    ctx.db.flush()
    return {"id": str(imp.id), "file_name": imp.file_name, "status": imp.status, "row_count": len(rows), "mapping": mapping,
            "preview": rows[:5], "errors": errors[:50]}
