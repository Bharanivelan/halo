"""The agent's "harness" (D-47): the tunable parts of Halo, saved as numbered agent versions.

harness = {
  "scoring": {"weights": {...}, "params": {...}},   # same shape as a scoring_models row
  "classify_guidance": "...",                       # extra hotel-specific rules for the company-sorting step
}

Only the parts listed in TUNABLE can be changed by the Lab, each within safe bounds. The evidence rules,
the untrusted-content rule, the output formats and the research/signal prompts are locked (not in here).
"""
from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.vocab import EMPLOYEE_RANGES, INDUSTRIES
from app.models import AgentVersion, ScoringModel
from app.scoring.engine import DEFAULT_MODEL

GUIDANCE_MAX_CHARS = 1200

# path -> (plain label, min, max, kind)  kind: "int" | "float"
TUNABLE: dict[str, tuple[str, float, float, str]] = {
    "weights.fit.industry": ("Weight on industry match", 0, 60, "int"),
    "weights.fit.inbound_travel": ("Weight on visitors travelling in", 0, 60, "int"),
    "weights.fit.proximity": ("Weight on distance to the hotel", 0, 60, "int"),
    "weights.fit.scale": ("Weight on company size", 0, 60, "int"),
    "weights.priority.fit": ("Share of the score from fit (the rest is buying signals)", 0.3, 0.9, "float"),
    "params.tiers.A": ("Score needed for Hot", 30, 90, "int"),
    "params.tiers.B": ("Score needed for Warm", 15, 80, "int"),
    "params.proximity.full_km": ("Distance that counts as right next door (km)", 0.5, 10, "float"),
    "params.proximity.edge_value": ("Credit for companies at the edge of the radius", 0, 1, "float"),
    "params.inbound_travel.hq_outside_city": ("Credit for a head office in another city", 0, 0.6, "float"),
    "params.inbound_travel.client_facing": ("Credit for client-facing services", 0, 0.6, "float"),
    "params.inbound_travel.multi_location": ("Credit for several office locations", 0, 0.6, "float"),
    "params.inbound_travel.training": ("Credit for training or onboarding", 0, 0.6, "float"),
    "params.inbound_travel.travel_indicators": ("Credit for other travel clues", 0, 0.6, "float"),
}
for _r in EMPLOYEE_RANGES:
    TUNABLE[f"params.scale_curve.{_r}"] = (f"Value of companies with {_r} staff", 0, 1, "float")
for _code, (_label, _rel) in INDUSTRIES.items():
    TUNABLE[f"params.industry_adjust.{_code}"] = (f"Extra preference for {_label}", -0.5, 0.5, "float")


def default_harness(scoring: dict | None = None) -> dict:
    s = copy.deepcopy(scoring or {"weights": DEFAULT_MODEL["weights"], "params": DEFAULT_MODEL["params"]})
    s["params"].setdefault("industry_adjust", {})
    return {"scoring": s, "classify_guidance": ""}


def _get(h: dict, path: str) -> Any:
    node: Any = h["scoring"]
    for k in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(k)
    return node


def _set(h: dict, path: str, value: Any) -> None:
    node = h["scoring"]
    keys = path.split(".")
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value


def label(path: str) -> str:
    return TUNABLE.get(path, (path,))[0]


def fmt(v: Any) -> str:
    if v is None:
        return "default"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) < 10 else f"{v:.1f}"
    return str(v)


def apply_edits(base: dict, edits: list[dict] | None, guidance: str | None = None) -> tuple[dict, list[str]]:
    """Apply proposed edits safely. Unknown paths are ignored, values are clamped. Returns (harness, plain changes)."""
    h = copy.deepcopy(base)
    h["scoring"]["params"].setdefault("industry_adjust", {})
    changes: list[str] = []
    for e in edits or []:
        path, to = str(e.get("path", "")), e.get("to")
        if path not in TUNABLE or not isinstance(to, (int, float)) or isinstance(to, bool):
            continue
        lbl, lo, hi, kind = TUNABLE[path]
        v: float = min(hi, max(lo, float(to)))
        v = int(round(v)) if kind == "int" else round(v, 3)
        before = _get(h, path)
        if before is not None and abs(float(before) - v) < 1e-9:
            continue
        if before is None and path.startswith("params.industry_adjust.") and v == 0:
            continue
        _set(h, path, v)
        changes.append(f"{lbl}: {fmt(before if before is not None else 0 if 'industry_adjust' in path else None)} → {fmt(v)}")
    # Keep the pieces consistent.
    w = h["scoring"]["weights"]
    w["priority"]["intent"] = round(1 - float(w["priority"]["fit"]), 3)
    t = h["scoring"]["params"]["tiers"]
    if t["B"] > t["A"] - 5:
        t["B"] = max(15, int(t["A"]) - 5)
    if guidance is not None:
        g = " ".join(str(guidance).split())[:GUIDANCE_MAX_CHARS]
        if g != h.get("classify_guidance", ""):
            h["classify_guidance"] = g
            changes.append("Sorting guidance updated: " + (f"“{g[:140]}{'…' if len(g) > 140 else ''}”" if g else "removed"))
    return h, changes


def tunable_snapshot(h: dict) -> dict[str, Any]:
    """Current values of every tunable setting, for the AI editor."""
    out = {}
    for path in TUNABLE:
        v = _get(h, path)
        if v is None and path.startswith("params.industry_adjust."):
            continue
        out[path] = v
    return out


# ───────── versions ─────────
def active_version(db: Session, workspace_id: UUID) -> AgentVersion:
    """The live agent version. Created on first use from the workspace's current scoring model (version 1)."""
    v = db.execute(select(AgentVersion).where(AgentVersion.status == "active")
                   .order_by(AgentVersion.version.desc())).scalars().first()
    if v:
        return v
    sm = db.execute(select(ScoringModel).where(ScoringModel.is_active.is_(True))
                    .order_by(ScoringModel.version.desc())).scalars().first()
    scoring = {"weights": sm.weights, "params": sm.params} if sm else None
    last = db.execute(select(AgentVersion.version).order_by(AgentVersion.version.desc())).scalars().first() or 0
    v = AgentVersion(workspace_id=workspace_id, version=last + 1, status="active", harness=default_harness(scoring),
                     changes=[], metrics={}, summary="Starting version: Halo's built-in rules.")
    db.add(v)
    db.flush()
    return v


def classify_guidance(db: Session, workspace_id: UUID) -> tuple[str, int]:
    v = active_version(db, workspace_id)
    return (v.harness or {}).get("classify_guidance") or "", v.version


def activate(db: Session, workspace_id: UUID, v: AgentVersion, user_id: UUID | None) -> ScoringModel:
    """Make `v` the live version: retire the old one and install its scoring rules as a new scoring model."""
    from datetime import datetime, timezone

    db.execute(update(AgentVersion).where(AgentVersion.status == "active", AgentVersion.id != v.id).values(status="retired"))
    v.status, v.decided_by, v.decided_at = "active", user_id, datetime.now(timezone.utc)
    db.execute(update(ScoringModel).where(ScoringModel.is_active.is_(True)).values(is_active=False))
    last = db.execute(select(ScoringModel.version).order_by(ScoringModel.version.desc())).scalars().first() or 0
    sm = ScoringModel(workspace_id=workspace_id, version=last + 1, weights=v.harness["scoring"]["weights"],
                      params=v.harness["scoring"]["params"], is_active=True, notes=f"Agent version {v.version} (Halo Lab)")
    db.add(sm)
    db.flush()
    return sm
