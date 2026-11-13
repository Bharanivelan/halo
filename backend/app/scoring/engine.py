"""Deterministic, explainable scoring v1 (AGENT_ARCHITECTURE §8, DD-09…DD-11).

Pure functions: same inputs + same model params → same score. All weights and curves come
from the versioned `scoring_models` row; DEFAULT_MODEL is only used to seed a workspace.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import median
from typing import Any

from app.core.vocab import INDUSTRIES, KEY_FIELDS, SIGNAL_TYPES

DEFAULT_MODEL: dict[str, Any] = {
    "weights": {"fit": {"industry": 30, "inbound_travel": 30, "proximity": 20, "scale": 20},
                "priority": {"fit": 0.6, "intent": 0.4}},
    "params": {
        "tiers": {"A": 65, "B": 45},
        "inbound_travel": {"hq_outside_city": 0.35, "client_facing": 0.25, "multi_location": 0.15,
                           "training": 0.15, "travel_indicators": 0.10, "inference_factor": 0.5},
        "proximity": {"full_km": 3.0, "edge_value": 0.3, "zero_at_radius_x": 1.5},
        "scale_curve": {"1-10": 0.1, "11-50": 0.3, "51-200": 0.6, "201-500": 0.9, "501-1000": 1.0,
                        "1001-5000": 0.8, "5000+": 0.6},
        "signals": {code: {"strength": v[2], "half_life_days": v[3]} for code, v in SIGNAL_TYPES.items()},
        "signal_window_days": 365,
        "intent_saturation": 1.5,
        "fresh_days": 90,
        "confidence": {"coverage": 40, "diversity": 30, "freshness": 30, "freshness_half_life_days": 365},
    },
}


@dataclass
class ClaimIn:
    id: str
    field: str
    value: Any
    kind: str
    source_domain: str | None = None
    source_date: datetime | None = None


@dataclass
class SignalIn:
    id: str
    signal_type: str
    title: str
    published_at: datetime | None
    confidence: float


@dataclass
class ScoreInput:
    industry_code: str | None
    offerings: list[str]
    property_city: str | None
    distance_km: float | None
    radius_km: float
    claims: list[ClaimIn]
    signals: list[SignalIn]
    has_contact: bool
    has_roles: bool
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _current(claims: list[ClaimIn], fld: str) -> ClaimIn | None:
    best = None
    for c in claims:
        if c.field != fld or c.kind == "unknown":
            continue
        if best is None or (c.kind == "fact" and best.kind != "fact"):
            best = c
    return best


def _truthy(v: Any) -> bool:
    if isinstance(v, dict):
        v = v.get("value", v.get("answer"))
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "y", "1")
    return bool(v)


def age_days(d: datetime | None, now: datetime) -> float | None:
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return max(0.0, (now - d).total_seconds() / 86400)


def signal_contribution(sig: SignalIn, params: dict, now: datetime) -> float:
    a = age_days(sig.published_at, now)
    if a is None or a > params["signal_window_days"]:
        return 0.0
    sp = params["signals"].get(sig.signal_type, {"strength": 0.4, "half_life_days": 90})
    return sp["strength"] * max(0.0, min(1.0, sig.confidence)) * math.pow(0.5, a / sp["half_life_days"])


def score(inp: ScoreInput, model: dict) -> dict:
    w, p = model["weights"], model["params"]
    fw = w["fit"]
    factors = []

    # Industry relevance
    ind_claim = _current(inp.claims, "industry")
    rel_map = INDUSTRIES.get(inp.industry_code or "", (None, {}))[1]
    ind_val = max((rel_map.get(o, 0.0) for o in inp.offerings), default=0.0) if inp.industry_code else 0.0
    # Hotel-specific preference learned by Halo Lab (D-47); absent = no change.
    adj = (p.get("industry_adjust") or {}).get(inp.industry_code or "", 0.0) if inp.industry_code else 0.0
    ind_val = max(0.0, min(1.0, ind_val + adj))
    label = INDUSTRIES.get(inp.industry_code or "", ("Unknown industry", {}))[0]
    factors.append({"key": "industry", "label": "Industry relevance", "weight": fw["industry"], "value": round(ind_val, 3),
                    "explanation": f"{label} · relevance to this hotel's offerings" if inp.industry_code else "Industry unknown",
                    "evidence": {"claims": [ind_claim.id] if ind_claim else []}})

    # Inbound travel potential
    itp = p["inbound_travel"]
    parts, ev, val = [], [], 0.0

    def credit(c: ClaimIn | None, amount: float, text: str) -> None:
        nonlocal val
        if c is None:
            return
        f = 1.0 if c.kind == "fact" else itp["inference_factor"]
        val += amount * f
        parts.append(text + ("" if c.kind == "fact" else " (inferred)"))
        ev.append(c.id)

    hq = _current(inp.claims, "hq_location")
    if hq and isinstance(hq.value, dict) and hq.value.get("city") and inp.property_city:
        if hq.value["city"].strip().lower() not in inp.property_city.strip().lower():
            credit(hq, itp["hq_outside_city"], f"HQ in {hq.value['city']}")
    cf = _current(inp.claims, "client_facing_services")
    if cf and _truthy(cf.value):
        credit(cf, itp["client_facing"], "client-facing services")
    ol = _current(inp.claims, "other_locations")
    if ol and isinstance(ol.value, list) and len(ol.value) >= 1:
        credit(ol, itp["multi_location"], f"{len(ol.value) + 1}+ locations")
    tr = _current(inp.claims, "has_training_or_onboarding")
    if tr and _truthy(tr.value):
        credit(tr, itp["training"], "training / onboarding")
    ti = _current(inp.claims, "travel_indicators")
    if ti and ti.value:
        credit(ti, itp["travel_indicators"], "travel indicators")
    val = min(1.0, val)
    factors.append({"key": "inbound_travel", "label": "Inbound travel potential", "weight": fw["inbound_travel"],
                    "value": round(val, 3), "explanation": "; ".join(parts) if parts else "No travel indicators verified yet",
                    "evidence": {"claims": ev}})

    # Proximity
    pp = p["proximity"]
    d = inp.distance_km
    if d is None:
        prox, pexp = 0.0, "Location unknown"
    elif d <= pp["full_km"]:
        prox, pexp = 1.0, f"{d:.1f} km from the property"
    elif d <= inp.radius_km:
        span = max(0.001, inp.radius_km - pp["full_km"])
        prox = 1.0 - (1.0 - pp["edge_value"]) * (d - pp["full_km"]) / span
        pexp = f"{d:.1f} km from the property"
    elif d <= inp.radius_km * pp["zero_at_radius_x"]:
        span = max(0.001, inp.radius_km * (pp["zero_at_radius_x"] - 1))
        prox = pp["edge_value"] * (1 - (d - inp.radius_km) / span)
        pexp = f"{d:.1f} km — outside the {inp.radius_km:g} km radius"
    else:
        prox, pexp = 0.0, f"{d:.1f} km — far outside the radius"
    loc = _current(inp.claims, "local_presence")
    factors.append({"key": "proximity", "label": "Proximity", "weight": fw["proximity"], "value": round(max(0.0, prox), 3),
                    "explanation": pexp, "evidence": {"claims": [loc.id] if loc else []}})

    # Scale
    emp = _current(inp.claims, "employee_range")
    rng = emp.value if emp and isinstance(emp.value, str) else (emp.value.get("range") if emp and isinstance(emp.value, dict) else None)
    sc = p["scale_curve"].get(rng or "", 0.0)
    if emp and emp.kind != "fact":
        sc *= 0.5
    factors.append({"key": "scale", "label": "Company scale", "weight": fw["scale"], "value": round(sc, 3),
                    "explanation": f"{rng} employees" if rng else "Employee range not verified",
                    "evidence": {"claims": [emp.id] if emp else []}})

    for f in factors:
        f["points"] = round(f["weight"] * f["value"], 1)
    fit = round(sum(f["points"] for f in factors))

    # Intent
    sig_rows = []
    total = 0.0
    for s in inp.signals:
        c = signal_contribution(s, p, inp.now)
        a = age_days(s.published_at, inp.now)
        sig_rows.append({"id": s.id, "title": s.title, "signal_type": s.signal_type, "contribution": round(c, 3),
                         "age_days": round(a) if a is not None else None})
        total += c
    sig_rows.sort(key=lambda r: -r["contribution"])
    intent = round(min(100.0, 100.0 * total / p["intent_saturation"]))

    # Confidence (about the data, not the company)
    cp = p["confidence"]
    facts = [c for c in inp.claims if c.kind == "fact"]
    coverage = sum(1 for k in KEY_FIELDS if any(c.field == k for c in facts) or (k == "industry" and inp.industry_code)) / len(KEY_FIELDS)
    domains = {c.source_domain for c in facts if c.source_domain}
    diversity = min(1.0, len(domains) / 3)
    ages = [age_days(c.source_date, inp.now) for c in facts if c.source_date]
    ages = [a for a in ages if a is not None]
    freshness = math.pow(0.5, median(ages) / cp["freshness_half_life_days"]) if ages else 0.0
    confidence = round(cp["coverage"] * coverage + cp["diversity"] * diversity + cp["freshness"] * freshness)

    actionability = "contact_available" if inp.has_contact else ("roles_identified" if inp.has_roles else "none")
    pw = w["priority"]
    priority = round(pw["fit"] * fit + pw["intent"] * intent, 1)
    tiers = p["tiers"]
    tier = "A" if priority >= tiers["A"] else "B" if priority >= tiers["B"] else "C"
    missing = [k for k in KEY_FIELDS if not any(c.field == k and c.kind == "fact" for c in inp.claims)]

    return {
        "fit": fit, "intent": intent, "confidence": confidence, "priority": priority, "tier": tier,
        "actionability": actionability,
        "breakdown": {
            "fit": {"total": fit, "factors": factors},
            "intent": {"total": intent, "signals": sig_rows},
            "confidence": {"total": confidence, "components": {"coverage": round(coverage, 2),
                                                                "diversity": round(diversity, 2),
                                                                "freshness": round(freshness, 2)}},
            "missing": missing,
        },
    }


# Role recommendations (AGENT_ARCHITECTURE §10)
ROLE_RULES = {
    "corporate_rate": {"small": ["founder_ceo", "operations_head", "admin_facilities"],
                       "large": ["admin_facilities", "travel_desk", "procurement"]},
    "mice": {"small": ["founder_ceo", "hr_manager"], "large": ["hr_manager", "events_marketing", "admin_facilities"]},
    "long_stay": {"small": ["operations_head", "hr_manager"], "large": ["talent_acquisition", "admin_facilities"]},
    "fnb": {"small": ["admin_facilities", "hr_manager"], "large": ["admin_facilities", "hr_manager"]},
}
ROLE_WHY = {
    "founder_ceo": "In smaller firms the founder usually decides on hotel partners.",
    "operations_head": "Runs day-to-day operations, including visitor logistics.",
    "admin_facilities": "Typically books hotels for visitors and manages corporate rate agreements.",
    "travel_desk": "Owns business-travel bookings and preferred-hotel programmes.",
    "procurement": "Negotiates and approves vendor contracts in larger companies.",
    "hr_manager": "Organises offsites, town halls and employee events.",
    "talent_acquisition": "Arranges stays for new joiners, interview candidates and relocations.",
    "events_marketing": "Plans conferences, launches and client events.",
    "plant_head": "Hosts vendors, auditors and technical visitors at the plant.",
}


def recommend_roles(employee_range: str | None, offerings: list[str], industry_code: str | None) -> list[dict]:
    small = employee_range in ("1-10", "11-50", "51-200")
    out, seen, rank = [], set(), 1
    for off in offerings:
        roles = ROLE_RULES.get(off, {}).get("small" if small else "large", [])
        if industry_code and industry_code.startswith("manufacturing") and off == "corporate_rate":
            roles = ["plant_head"] + roles
        for r in roles:
            if r in seen:
                continue
            seen.add(r)
            out.append({"role_code": r, "offering": off, "rank": rank, "rationale": ROLE_WHY.get(r, "")})
            rank += 1
    return out[:4]
