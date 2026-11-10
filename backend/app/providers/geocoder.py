"""Geocoding via OSM Nominatim (DD-07). Usage policy: ≤ 1 request/second, identify the app, cache results."""
from __future__ import annotations

from functools import lru_cache

import httpx

from app.core.config import get_settings
from app.providers.http import Throttle, client, raise_for_status

_settings = get_settings()
_throttle = Throttle(1.1)


@lru_cache(maxsize=512)
def geocode(q: str, limit: int = 6) -> tuple[dict, ...]:
    _throttle.wait("nominatim")
    try:
        r = client.get(f"{_settings.nominatim_url}/search",
                       params={"q": q, "format": "jsonv2", "addressdetails": 1, "limit": limit}, timeout=12)
    except httpx.HTTPError:
        return ()
    raise_for_status(r, "Geocoder")
    out = []
    for it in r.json():
        a = it.get("address", {})
        out.append({
            "label": it.get("display_name"),
            "lat": float(it["lat"]), "lng": float(it["lon"]),
            "locality": a.get("suburb") or a.get("neighbourhood") or a.get("village") or a.get("town"),
            "city": a.get("city") or a.get("town") or a.get("county") or a.get("state_district"),
            "state": a.get("state"), "postal_code": a.get("postcode"), "country": (a.get("country_code") or "").upper() or None,
        })
    return tuple(out)


@lru_cache(maxsize=512)
def reverse(lat: float, lng: float) -> dict | None:
    _throttle.wait("nominatim")
    try:
        r = client.get(f"{_settings.nominatim_url}/reverse",
                       params={"lat": lat, "lon": lng, "format": "jsonv2", "addressdetails": 1, "zoom": 14}, timeout=12)
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    a = r.json().get("address", {})
    return {"locality": a.get("suburb") or a.get("neighbourhood"), "city": a.get("city") or a.get("town") or a.get("county")}
