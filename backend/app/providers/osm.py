"""OpenStreetMap discovery via the Overpass API (free; ODbL attribution required).

Public Overpass servers are often at capacity, so we rotate endpoints and back off.
"""
from __future__ import annotations

import time

import httpx

from app.core.config import get_settings
from app.providers.http import Throttle, client
from app.workflow.errors import TransientError

_settings = get_settings()
_throttle = Throttle(2.0)

# Industry code → Overpass selectors. Anything with an "office" tag is a candidate for
# office-type industries; classification decides the actual industry.
OFFICE_INDUSTRIES = {
    "it_services", "it_product_saas", "ites_bpo", "engineering_rnd", "consulting_professional",
    "bfsi_operations", "logistics", "real_estate_coworking", "events_agency", "travel_management", "other",
}
SELECTORS = {
    "office": ['nwr["office"]["name"]'],
    "manufacturing": ['nwr["industrial"]["name"]', 'nwr["man_made"="works"]["name"]', 'nwr["building"="industrial"]["name"]'],
    "education": ['nwr["amenity"~"^(college|university)$"]["name"]'],
    "healthcare": ['nwr["amenity"="hospital"]["name"]', 'nwr["healthcare"="hospital"]["name"]'],
}


def selector_groups(industries: list[str]) -> list[str]:
    groups: set[str] = set()
    for code in industries or ["it_services"]:
        if code in OFFICE_INDUSTRIES:
            groups.add("office")
        elif code.startswith("manufacturing"):
            groups.add("manufacturing")
        elif code == "education":
            groups.add("education")
        elif code == "healthcare_hospital":
            groups.add("healthcare")
    return sorted(groups) or ["office"]


def build_query(lat: float, lng: float, radius_m: int, groups: list[str]) -> str:
    parts = []
    for g in groups:
        for sel in SELECTORS[g]:
            parts.append(f"{sel}(around:{radius_m},{lat:.6f},{lng:.6f});")
    return f"[out:json][timeout:{_settings.overpass_timeout_s}];({''.join(parts)});out center tags;"


def query(lat: float, lng: float, radius_km: float, industries: list[str]) -> tuple[list[dict], str]:
    """Returns (candidates, endpoint_used). Each candidate: name, lat, lng, osm_id, tags."""
    q = build_query(lat, lng, int(radius_km * 1000), selector_groups(industries))
    last_err = "no endpoint tried"
    for attempt, ep in enumerate(_settings.overpass_endpoints * 2):
        _throttle.wait("overpass")
        try:
            r = client.get(ep, params={"data": q}, timeout=_settings.overpass_timeout_s + 20)
        except httpx.HTTPError as e:
            last_err = f"{type(e).__name__} at {ep}"
            continue
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            return _parse(r.json()), ep
        last_err = f"HTTP {r.status_code} at {ep}"
        time.sleep(min(20, 3 * (attempt + 1)))
    raise TransientError(f"OpenStreetMap (Overpass) is busy: {last_err}", retry_after_s=60)


def _parse(data: dict) -> list[dict]:
    out = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name:en") or tags.get("name") or "").strip()
        if not name:
            continue
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lng = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lng is None:
            continue
        website = tags.get("website") or tags.get("contact:website") or tags.get("url")
        addr = ", ".join(v for k in ("addr:housenumber", "addr:street", "addr:suburb", "addr:city", "addr:postcode")
                         if (v := tags.get(k)))
        out.append({
            "name": name, "lat": float(lat), "lng": float(lng), "osm_id": f"{el['type']}/{el['id']}",
            "website": website, "address": addr or None, "locality": tags.get("addr:suburb"),
            "city": tags.get("addr:city"), "tags": tags,
        })
    return out
