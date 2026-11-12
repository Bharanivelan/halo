"""Supported markets (D-39). A project's country decides its currency, distance unit and address-search scope.

Distances are always stored in kilometres; the UI converts for display. Add a market by adding a row here.
"""
from __future__ import annotations

DEFAULT_COUNTRY = "US"

REGIONS: dict[str, dict] = {
    "US": {"code": "US", "label": "United States", "currency": "USD", "distance_unit": "mi", "locale": "en-US",
           "default_radius_km": 8.047},   # 5 miles
    "IN": {"code": "IN", "label": "India", "currency": "INR", "distance_unit": "km", "locale": "en-IN",
           "default_radius_km": 8.0},
}


def region(country: str | None) -> dict:
    return REGIONS.get((country or "").upper(), REGIONS[DEFAULT_COUNTRY])
