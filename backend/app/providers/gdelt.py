"""News signals via the GDELT DOC 2.0 API (free). Rate limit: one request per ~5 seconds (global)."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.providers.http import Throttle, client
from app.workflow.errors import TransientError

_settings = get_settings()
_throttle = Throttle(_settings.gdelt_min_interval_s)


def search(company_name: str, city: str | None, max_records: int = 15) -> list[dict]:
    name = company_name.replace('"', "").strip()
    if len(name) < 4:
        return []
    place = f' ("{city}" OR India)' if city else " India"
    q = f'"{name}"{place}'
    _throttle.wait("gdelt")
    try:
        r = client.get(_settings.gdelt_url, params={
            "query": q, "mode": "artlist", "format": "json", "maxrecords": max_records,
            "sort": "datedesc", "timespan": "3months"}, timeout=25)
    except httpx.HTTPError as e:
        raise TransientError(f"GDELT news search failed ({type(e).__name__})") from e
    if r.status_code == 429 or "limit requests" in r.text[:200]:
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
