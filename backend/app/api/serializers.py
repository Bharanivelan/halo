"""Row → JSON serializers. Output shapes match frontend/src/api/types.ts exactly."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.regions import region
from app.core.vocab import CLAIM_FIELDS, INDUSTRIES, ROLE_CODES, SIGNAL_TYPES
from app.models import (Account, ActivityRow, Claim, Company, CompanyLocation, Contact, DiscoveryJob, Membership,
                        Opportunity, Property, PropertyAccess, PropertyOffering, PropertyTargetProfile, Signal, Source,
                        User, Workspace)
from app.providers.fetcher import registrable_domain


def iso(d: datetime | date | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return d.isoformat()


def num(v) -> float | None:
    return float(v) if v is not None else None


def point(geo) -> dict | None:
    if geo is None:
        return None
    if isinstance(geo, str):  # freshly assigned WKT, e.g. "SRID=4326;POINT(lng lat)"
        import re
        m = re.search(r"POINT\(([-\d.]+) ([-\d.]+)\)", geo)
        return {"lat": float(m.group(2)), "lng": float(m.group(1))} if m else None
    p = to_shape(geo)
    return {"lat": p.y, "lng": p.x}


def age_days(d: datetime | None) -> int | None:
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - d).days)


# ───────── identity ─────────
def member_name(db: Session, membership_id: UUID | None) -> dict | None:
    if not membership_id:
        return None
    row = db.execute(select(User.full_name).join(Membership, Membership.user_id == User.id)
                     .where(Membership.id == membership_id)).first()
    return {"id": str(membership_id), "name": row[0]} if row else None


def me_payload(db: Session, *, user_id, workspace_id, membership_id, role, csrf) -> dict:
    user = db.get(User, user_id)
    ws = db.get(Workspace, workspace_id)
    q = select(Property).where(Property.archived_at.is_(None)).order_by(Property.created_at)
    if role == "rep":
        q = q.where(Property.id.in_(select(PropertyAccess.property_id).where(PropertyAccess.membership_id == membership_id)))
    props = db.execute(q).scalars().all()
    return {
        "user": {"id": str(user.id), "email": user.email, "full_name": user.full_name},
        "workspace": {"id": str(ws.id), "name": ws.name, "is_demo": ws.is_demo},
        "role": role, "membership_id": str(membership_id), "csrf_token": csrf,
        "properties": [property_summary(db, p) for p in props],
    }


# ───────── properties ─────────
def _target(db: Session, prop_id: UUID) -> PropertyTargetProfile | None:
    return db.execute(select(PropertyTargetProfile).where(PropertyTargetProfile.property_id == prop_id)).scalar_one_or_none()


def property_summary(db: Session, p: Property) -> dict:
    t = _target(db, p.id)
    count = db.execute(select(func.count()).select_from(Account).where(Account.property_id == p.id)).scalar_one()
    job = db.execute(select(DiscoveryJob).where(DiscoveryJob.property_id == p.id, DiscoveryJob.kind == "discovery")
                     .order_by(DiscoveryJob.created_at.desc()).limit(1)).scalar_one_or_none()
    r = region(p.country)
    return {"id": str(p.id), "name": p.name, "brand": p.brand, "locality": p.locality, "city": p.city,
            "lifecycle": p.lifecycle, "opening_date": iso(p.opening_date), "is_hypothetical": p.is_hypothetical,
            "location": point(p.location), "radius_km": t.radius_km if t else 15, "account_count": count,
            "country": r["code"], "currency": r["currency"], "distance_unit": r["distance_unit"],
            "created_at": iso(p.created_at),
            "latest_job": ({"id": str(job.id), "status": job.status, "created_at": iso(job.created_at),
                            "finished_at": iso(job.finished_at)} if job else None)}


def property_full(db: Session, p: Property) -> dict:
    t = _target(db, p.id)
    offerings = db.execute(select(PropertyOffering.offering).where(PropertyOffering.property_id == p.id)).scalars().all()
    return {**property_summary(db, p), "address_line": p.address_line, "state": p.state, "postal_code": p.postal_code,
            "rooms_count": p.rooms_count, "meeting_rooms_count": p.meeting_rooms_count,
            "largest_meeting_capacity": p.largest_meeting_capacity, "banquet_capacity": p.banquet_capacity,
            "restaurants_count": p.restaurants_count, "facilities": p.facilities or [], "description": p.description,
            "offerings": list(offerings),
            "target": {"radius_km": t.radius_km if t else 15, "industries": t.industries if t else [],
                       "employee_min": t.employee_min if t else None, "employee_max": t.employee_max if t else None,
                       "notes": t.notes if t else None},
            }


# ───────── evidence ─────────
def source_ref(s: Source | None) -> dict | None:
    if s is None:
        return None
    return {"id": str(s.id), "url": s.url, "title": s.title, "source_type": s.source_type, "retrieved_at": iso(s.retrieved_at),
            "published_at": iso(s.published_at), "domain": registrable_domain(s.url) if s.url else None}


def display_value(field: str, v: Any) -> str:
    if v is None:
        return "Not verified"
    if field == "industry":
        return INDUSTRIES.get(v, (str(v),))[0]
    if field == "hq_location" and isinstance(v, dict):
        return ", ".join(x for x in (v.get("city"), v.get("country")) if x)
    if field == "local_presence" and isinstance(v, dict):
        t = v.get("type")
        return (v.get("address") or "") + (f" ({t.replace('_', ' ')})" if t and t != "unknown" else "")
    if isinstance(v, dict) and "value" in v:
        base = "Yes" if v.get("value") else "No"
        return f"{base} — {v['note']}" if v.get("note") else base
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if field == "employee_range":
        return f"{v} employees"
    return str(v)


def claim_out(c: Claim, s: Source | None) -> dict:
    return {"id": str(c.id), "field": c.field, "field_label": CLAIM_FIELDS.get(c.field, c.field), "value": c.value,
            "display_value": display_value(c.field, c.value), "kind": c.kind, "confidence": c.confidence,
            "grounding_status": c.grounding_status, "evidence_quote": c.evidence_quote if c.kind == "fact" else None,
            "rationale": c.rationale, "supports": [str(x) for x in (c.supports or [])], "source": source_ref(s),
            "data_origin": c.data_origin}


def signal_out(sg: Signal, s: Source | None, window_days: int = 365) -> dict:
    a = age_days(sg.published_at)
    return {"id": str(sg.id), "signal_type": sg.signal_type, "type_label": SIGNAL_TYPES.get(sg.signal_type, (sg.signal_type,))[0],
            "title": sg.title, "description": sg.description, "published_at": iso(sg.published_at), "age_days": a,
            "is_historical": a is None or a > window_days, "confidence": sg.confidence,
            "implied_offerings": sg.implied_offerings or [], "recommended_approach": sg.recommended_approach,
            "evidence_quote": sg.evidence_quote, "source": source_ref(s)}


# ───────── accounts ─────────
def company_brief(c: Company, locality: str | None) -> dict:
    return {"id": str(c.id), "name": c.name, "domain": c.primary_domain, "industry": c.industry_code,
            "industry_label": INDUSTRIES.get(c.industry_code or "", (None,))[0], "employee_range": c.employee_range,
            "locality": locality, "data_origin": c.data_origin}


def best_signals(db: Session, company_ids: list[UUID], window_days: int = 365) -> dict[UUID, Signal]:
    if not company_ids:
        return {}
    rows = db.execute(select(Signal).where(Signal.company_id.in_(company_ids)).order_by(Signal.published_at.desc().nullslast())).scalars().all()
    out: dict[UUID, Signal] = {}
    for s in rows:
        a = age_days(s.published_at)
        if a is None or a > window_days:
            continue
        cur = out.get(s.company_id)
        if cur is None or s.confidence * (0.5 ** (a / 120)) > cur.confidence * (0.5 ** ((age_days(cur.published_at) or 0) / 120)):
            out[s.company_id] = s
    return out


def localities(db: Session, company_ids: list[UUID]) -> dict[UUID, str | None]:
    if not company_ids:
        return {}
    rows = db.execute(select(CompanyLocation.company_id, CompanyLocation.locality, CompanyLocation.city)
                      .where(CompanyLocation.company_id.in_(company_ids))).all()
    out: dict[UUID, str | None] = {}
    for cid, loc, city in rows:
        out.setdefault(cid, loc or city)
    return out


def account_items(db: Session, rows: list[tuple[Account, Company]]) -> list[dict]:
    cids = [c.id for _, c in rows]
    sigs, locs = best_signals(db, cids), localities(db, cids)
    owners = {a.owner_membership_id for a, _ in rows if a.owner_membership_id}
    names = {}
    if owners:
        names = {mid: n for mid, n in db.execute(select(Membership.id, User.full_name).join(User, User.id == Membership.user_id)
                                                  .where(Membership.id.in_(owners))).all()}
    out = []
    for a, c in rows:
        s = sigs.get(c.id)
        out.append({
            "id": str(a.id), "property_id": str(a.property_id), "company": company_brief(c, locs.get(c.id)),
            "distance_km": a.distance_km, "tier": a.tier, "priority": a.priority, "fit": a.fit, "intent": a.intent,
            "confidence": a.confidence, "actionability": a.actionability,
            "top_signal": ({"type": s.signal_type, "type_label": SIGNAL_TYPES.get(s.signal_type, (s.signal_type,))[0],
                            "title": s.title, "age_days": age_days(s.published_at)} if s else None),
            "status": a.status,
            "owner": ({"id": str(a.owner_membership_id), "name": names.get(a.owner_membership_id, "")} if a.owner_membership_id else None),
            "research_status": c.research_status, "updated_at": iso(a.updated_at),
        })
    return out


def contact_out(c: Contact, company_name: str | None = None, account_id: UUID | None = None) -> dict:
    d = {"id": str(c.id), "company_id": str(c.company_id), "full_name": c.full_name, "title": c.title, "role_code": c.role_code,
         "email": c.email, "phone": c.phone, "profile_url": c.profile_url, "source_note": c.source_note,
         "verification_status": c.verification_status, "do_not_contact": c.do_not_contact, "created_at": iso(c.created_at)}
    if company_name is not None:
        d["company_name"] = company_name
    if account_id is not None:
        d["account_id"] = str(account_id)
    return d


def opportunity_out(db: Session, o: Opportunity, company_name: str | None = None) -> dict:
    if company_name is None:
        company_name = db.execute(select(Company.name).join(Account, Account.company_id == Company.id)
                                  .where(Account.id == o.account_id)).scalar_one()
    return {"id": str(o.id), "account_id": str(o.account_id), "company_name": company_name, "name": o.name,
            "offering": o.offering, "stage": o.stage, "value_amount": num(o.value_amount), "currency": o.currency,
            "expected_close_date": iso(o.expected_close_date), "probability": o.probability,
            "owner": member_name(db, o.owner_membership_id), "loss_reason": o.loss_reason, "loss_note": o.loss_note,
            "updated_at": iso(o.updated_at)}


def activity_out(db: Session, a: ActivityRow) -> dict:
    return {"id": str(a.id), "type": a.type, "body": a.body, "occurred_at": iso(a.occurred_at),
            "actor": member_name(db, a.actor_membership_id), "opportunity_id": str(a.opportunity_id) if a.opportunity_id else None,
            "metadata": a.meta or {}}


def role_label(code: str) -> str:
    return ROLE_CODES.get(code, code)
