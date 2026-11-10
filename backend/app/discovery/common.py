"""Shared helpers for discovery steps: names, distance, sources and grounded claims."""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.evidence.grounding import check_quote, value_consistent
from app.models import Claim, Source

LEGAL = re.compile(
    r"\b(private|pvt|limited|ltd|llp|inc|incorporated|corp|corporation|co|company|plc|gmbh|india|the)\b\.?", re.I)


def normalize_name(name: str) -> str:
    n = name.lower().replace("&", " and ")
    n = LEGAL.sub(" ", n)
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()[:300] or name.lower()[:300]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def point_wkt(lat: float, lng: float) -> str:
    return f"SRID=4326;POINT({lng:.7f} {lat:.7f})"


def osm_tags_text(name: str, tags: dict) -> str:
    lines = [f"name={name}"] + [f"{k}={v}" for k, v in sorted(tags.items()) if k != "name"]
    return "\n".join(lines)


def save_source(db: Session, *, workspace_id: UUID, company_id: UUID | None, url: str | None, source_type: str,
                title: str | None, text: str | None, published_at: datetime | None = None, provider: str | None = None,
                license_tag: str = "public_web", job_id: UUID | None = None, http_status: int | None = None) -> Source:
    """Get-or-create by (company, url). Refreshes text so grounding uses the latest content."""
    settings = get_settings()
    existing = None
    if url and company_id:
        existing = db.execute(select(Source).where(Source.company_id == company_id, Source.url == url)
                              .order_by(Source.retrieved_at.desc()).limit(1)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    h = hashlib.sha256((text or "").encode()).digest() if text is not None else None
    if existing:
        existing.title = title or existing.title
        existing.content_text = text if text is not None else existing.content_text
        existing.content_hash = h or existing.content_hash
        existing.retrieved_at = now
        existing.published_at = published_at or existing.published_at
        existing.content_expires_at = now + timedelta(days=settings.page_text_retention_days)
        existing.job_id = job_id or existing.job_id
        return existing
    src = Source(workspace_id=workspace_id, company_id=company_id, url=url, canonical_url=url, source_type=source_type,
                 provider=provider, title=title, content_text=text, content_hash=h, published_at=published_at,
                 retrieved_at=now, content_expires_at=now + timedelta(days=settings.page_text_retention_days),
                 license_tag=license_tag, exportable=license_tag != "google_places", job_id=job_id, http_status=http_status)
    db.add(src)
    db.flush()
    return src


def supersede_auto_claims(db: Session, company_id: UUID) -> None:
    db.execute(update(Claim).where(Claim.company_id == company_id, Claim.is_current.is_(True),
                                   Claim.data_origin == "real").values(is_current=False))


def add_claim(db: Session, *, workspace_id: UUID, company_id: UUID, field: str, value, kind: str,
              source: Source | None = None, quote: str | None = None, confidence: float = 0.7,
              rationale: str | None = None, supports: list[UUID] | None = None, task_id: UUID | None = None,
              data_origin: str = "real") -> Claim:
    """Insert a claim, enforcing the evidence rules. A FACT whose quote isn't in its source becomes UNKNOWN."""
    grounding, detail = "not_applicable", {}
    if kind == "fact":
        if source is None or not quote:
            kind, grounding, detail = "unknown", "failed", {"reason": "fact without source or quote", "original_value": value}
        else:
            grounding, detail = check_quote(quote, source.content_text)
            if grounding == "failed" or not value_consistent(field, value, quote):
                if grounding != "failed":
                    detail = {"reason": "value not supported by quote"}
                    grounding = "failed"
                detail["original_value"] = value
                kind = "unknown"
    if kind == "unknown":
        value = None if grounding != "failed" else None
    claim = Claim(workspace_id=workspace_id, company_id=company_id, field=field, value=value, kind=kind,
                  source_id=source.id if source else None, evidence_quote=quote if kind == "fact" or grounding == "failed" else quote,
                  supports=supports or [], rationale=rationale, confidence=max(0.0, min(1.0, confidence)),
                  grounding_status=grounding, grounding_detail=detail, produced_by_task_id=task_id, data_origin=data_origin)
    if kind != "fact" and claim.grounding_status in ("passed", "passed_fuzzy"):
        claim.grounding_status = "not_applicable"
    db.add(claim)
    return claim


def parse_date(s) -> datetime | None:
    if not s:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    s = str(s).strip()[:25]
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%d %B %Y", "%B %d, %Y", "%Y-%m"):
        try:
            d = datetime.strptime(s.replace("Z", "+0000"), fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
