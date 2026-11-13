"""News signals via the GDELT DOC 2.0 API (free). Rate limit: one request per ~5 seconds (global)."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.providers.http import Throttle, client
from app.workflow.errors import TransientError

_settings = get_settings()
_throttle = Throttle(_settings.gdelt_min_interval_s)
_cool_until = 0.0  # after a rate-limit, skip news for a while instead of queueing every company behind it (D-45)
COOLDOWN_S = 120.0


def available() -> bool:
    return time.time() >= _cool_until


def search(company_name: str, city: str | None, country: str | None = None, max_records: int = 15) -> list[dict]:
    """Recent news for a company near the hotel. Raises TransientError when GDELT is busy (and starts a cooldown)."""
    global _cool_until
    name = company_name.replace('"', "").strip()
    if len(name) < 4:
        return []
    if not available():
        raise TransientError("GDELT news search is rate-limited")
    where = [f'"{x}"' for x in (city, country) if x]
    q = f'"{name}"' + (f' ({" OR ".join(where)})' if len(where) > 1 else f" {where[0]}" if where else "")
    _throttle.wait("gdelt")
    try:
        r = client.get(_settings.gdelt_url, params={
            "query": q, "mode": "artlist", "format": "json", "maxrecords": max_records,
            "sort": "datedesc", "timespan": "3months"}, timeout=15)
    except httpx.HTTPError as e:
        raise TransientError(f"GDELT news search failed ({type(e).__name__})") from e
    if r.status_code == 429 or "limit requests" in r.text[:200]:
        _cool_until = time.time() + COOLDOWN_S
        raise TransientError("GDELT news search is rate-limited", retry_after_s=10)
    if r.status_code != 200 or not r.text.strip().startswith("{"):
        return []
    out = []
    for a in r.json().get("articles", []):
        seen = a.get("seendate")  # e.g. 20261101T120000Z
        published = None
        if seen:
            try:
                published = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        out.append({"title": (a.get("title") or "").strip(), "url": a.get("url"), "domain": a.get("domain"),
                    "published_at": published, "language": a.get("language")})
    return [a for a in out if a["title"] and a["url"]]
