"""Discovery jobs: estimate, natural-language config, create, progress, cancel/resume/retry."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CtxDep
from app.api.serializers import iso, num
from app.core.config import get_settings
from app.core.errors import Conflict, FeatureUnavailable, NotFound, ValidationFailed
from app.core.vocab import INDUSTRIES, Offering
from app.models import Account, DiscoveryJob, DiscoveryResult, JobEvent, Membership, Property, User, WorkflowTask
from app.workflow import engine
from app.workflow.engine import NewTask

router = APIRouter(prefix="/discovery", tags=["discovery"])

STAGES = [("plan", "Understanding request & geography"), ("discover", "Discovering companies"),
          ("resolve", "Removing duplicates"), ("classify", "Filtering for relevance"),
          ("research", "Researching companies"), ("signals", "Identifying business signals"),
          ("score", "Scoring & validating evidence")]


class DiscoveryConfig(BaseModel):
    property_id: UUID
    radius_km: float = Field(15, ge=1, le=50)
    industries: list[str] = []
    employee_min: int | None = None
    employee_max: int | None = None
    offerings_focus: list[Offering] = []
    sources: list[str] = ["osm"]
    csv_import_id: UUID | None = None
    max_companies: int = Field(50, ge=1, le=200)
    research_depth: str = Field("standard", pattern="^(light|standard)$")
    signal_window_days: int = Field(365, ge=30, le=730)
    prioritisation_notes: str | None = Field(None, max_length=500)
    budget_usd: float = Field(5.0, gt=0, le=500)

    @field_validator("industries")
    @classmethod
    def known(cls, v):
        bad = [x for x in v if x not in INDUSTRIES]
        if bad:
            raise ValueError(f"Unknown industries: {', '.join(bad)}")
        return v

    @field_validator("sources")
    @classmethod
    def sources_ok(cls, v):
        allowed = {"osm", "csv", "web_search", "google_places"}
        if any(x not in allowed for x in v):
            raise ValueError("Unknown source")
        return v


class JobIn(BaseModel):
    config: DiscoveryConfig
    nl_request: str | None = None


class ParseIn(BaseModel):
    property_id: UUID
    text: str = Field(min_length=3, max_length=1000)
    current_config: DiscoveryConfig


class ResumeIn(BaseModel):
    budget_usd: float | None = Field(None, gt=0, le=500)


def estimate(db: Session, cfg: DiscoveryConfig) -> dict:
    s = get_settings()
    lo_m, mid_m, hi_m = s.estimate_multipliers
    n = cfg.max_companies
    cand = {"low": round(n * 0.5), "expected": round(n * 1.5), "high": round(n * 3)}
    researched = {k: min(n, round(v * s.estimate_pass_rate) or 1) for k, v in cand.items()}
    per_co = s.estimate_cost_per_company_usd[cfg.research_depth]
    is_cal = False
    # Calibrate from this workspace's recent finished jobs (actual spend per researched company).
    rows = db.execute(select(DiscoveryJob.id, DiscoveryJob.spent_usd).where(
        DiscoveryJob.status.in_(("completed", "completed_with_errors")), DiscoveryJob.spent_usd > 0)
        .order_by(DiscoveryJob.created_at.desc()).limit(5)).all()
    if rows:
        per = []
        for jid, spent in rows:
            k = db.execute(select(func.count()).select_from(WorkflowTask).where(
                WorkflowTask.job_id == jid, WorkflowTask.step == "research", WorkflowTask.status == "succeeded")).scalar_one()
            if k:
                per.append(float(spent) / k)
        if per:
            per_co, is_cal = sum(per) / len(per), True
    llm = s.llm_configured
    cost = {k: round(v * per_co * (1 if llm else 0), 2) for k, v in researched.items()}
    if is_cal:
        cost = {"low": round(cost["expected"] * lo_m, 2), "expected": cost["expected"], "high": round(cost["expected"] * hi_m, 2)}
    secs = s.estimate_seconds_per_company[cfg.research_depth]
    conc = max(1, s.worker_concurrency)
    dur = {k: round(2 + v * secs / conc / 60, 1) for k, v in researched.items()}
    warnings = []
    if not llm:
        warnings.append("AI is not configured: companies will be found and scored from map data, without website research or AI signals.")
    if "web_search" in cfg.sources and not s.search_configured:
        warnings.append("Web search is not configured; it will be skipped.")
    if "osm" in cfg.sources:
        warnings.append("OpenStreetMap coverage of offices varies by area; importing a CSV of known companies improves recall.")
    if cost["high"] > cfg.budget_usd:
        warnings.append(f"The high estimate (${cost['high']:.2f}) exceeds your budget cap; the job pauses at the cap.")
    return {"candidates": cand, "researched": researched, "cost_usd": cost, "duration_min": dur,
            "assumptions": [f"{cfg.research_depth} research depth",
                            f"≈ ${per_co:.3f} per researched company" + (" (measured from your recent jobs)" if is_cal else " (default, not yet measured)"),
                            f"pass rate {s.estimate_pass_rate:.0%} after relevance filtering", f"{conc} companies researched in parallel"],
            "is_calibrated": is_cal, "warnings": warnings}


def job_summary(db: Session, j: DiscoveryJob) -> dict:
    counts = engine.stage_counts(db, j.id)
    total = sum(sum(v.values()) for v in counts.values()) or 1
    done = sum(v["succeeded"] + v["failed"] + v["skipped"] for v in counts.values())
    found = 0
    for t in db.execute(select(WorkflowTask.output).where(WorkflowTask.job_id == j.id,
                                                          WorkflowTask.step.in_(("discover_osm", "discover_csv")),
                                                          WorkflowTask.status == "succeeded")).scalars():
        found += (t or {}).get("found", 0)
    companies = db.execute(select(func.count(func.distinct(DiscoveryResult.company_id))).where(
        DiscoveryResult.job_id == j.id, DiscoveryResult.account_id.is_not(None))).scalar_one()
    terminal = j.status in ("completed", "completed_with_errors", "failed", "cancelled")
    progress = 1.0 if terminal else min(0.99, done / total) if total > 1 else 0.02
    creator = db.execute(select(User.full_name).where(User.id == j.created_by)).scalar_one_or_none() if j.created_by else None
    prop_name = db.execute(select(Property.name).where(Property.id == j.property_id)).scalar_one()
    return {"id": str(j.id), "property_id": str(j.property_id), "property_name": prop_name, "status": j.status,
            "created_at": iso(j.created_at), "started_at": iso(j.started_at), "finished_at": iso(j.finished_at),
            "budget_usd": num(j.budget_usd), "spent_usd": round(num(j.spent_usd) or 0, 4), "reserved_usd": round(num(j.reserved_usd) or 0, 4),
            "progress": round(progress, 3),
            "counts": {"found": found, "companies": companies,
                       "researched": counts.get("research", {}).get("succeeded", 0),
                       "failed": sum(v["failed"] for v in counts.values()),
                       "scored": counts.get("score", {}).get("succeeded", 0)},
            "created_by": creator or "System"}


def job_detail(db: Session, j: DiscoveryJob) -> dict:
    counts = engine.stage_counts(db, j.id)
    outputs: dict[str, list[dict]] = {}
    for step_name, out in db.execute(select(WorkflowTask.step, WorkflowTask.output).where(
            WorkflowTask.job_id == j.id, WorkflowTask.step.in_(("plan", "discover_osm", "discover_csv", "resolve", "classify")),
            WorkflowTask.status == "succeeded")).all():
        outputs.setdefault(step_name, []).append(out or {})
    terminal = j.status in ("completed", "completed_with_errors", "failed", "cancelled")
    stages = []
    for key, label in STAGES:
        c = counts.get(key, {"pending": 0, "running": 0, "succeeded": 0, "failed": 0, "skipped": 0})
        tot = sum(c.values())
        if tot == 0:
            status = "skipped" if terminal else "pending"
        elif c["running"] or (c["pending"] and (c["succeeded"] or c["failed"])):
            status = "running"
        elif c["pending"]:
            status = "pending" if j.status != "running" else "running"
        elif c["failed"] and not c["succeeded"]:
            status = "failed"
        elif c["failed"]:
            status = "partial"
        elif c["skipped"] and not c["succeeded"]:
            status = "skipped"
        else:
            status = "succeeded"
        detail = None
        if key == "discover":
            f = sum(o.get("found", 0) for s in ("discover_osm", "discover_csv") for o in outputs.get(s, []))
            detail = f"{f} places found" if (outputs.get("discover_osm") or outputs.get("discover_csv")) else None
        elif key == "resolve" and outputs.get("resolve"):
            o = outputs["resolve"][0]
            detail = f"{o.get('new', 0)} companies · {o.get('merged', 0)} merged · {o.get('filtered', 0)} outside radius"
        elif key == "classify" and outputs.get("classify"):
            o = outputs["classify"][0]
            detail = f"{len(o.get('research', []))} to research · {o.get('dropped', 0)} filtered out"
        elif key in ("research", "signals", "score") and tot:
            detail = f"{c['succeeded']} of {tot} done" + (f" · {c['failed']} failed" if c["failed"] else "")
        stages.append({"key": key, "label": label, "status": status, "counts": c, "detail": detail})
    events = db.execute(select(JobEvent).where(JobEvent.job_id == j.id).order_by(JobEvent.id.desc()).limit(200)).scalars().all()
    return {**job_summary(db, j), "config": j.config, "estimate": j.estimate, "stages": stages,
            "events": [{"id": e.id, "level": e.level, "stage": e.stage, "message": e.message, "created_at": iso(e.created_at)}
                       for e in reversed(events)],
            "error": j.error}


def _job(ctx, job_id: UUID) -> DiscoveryJob:
    j = ctx.db.get(DiscoveryJob, job_id)
    if j is None:
        raise NotFound("Job not found")
    ctx.property(j.property_id)
    return j


@router.post("/estimate")
def post_estimate(body: dict, ctx: CtxDep):
    cfg = DiscoveryConfig.model_validate(body.get("config", body))
    ctx.property(cfg.property_id)
    return estimate(ctx.db, cfg)


@router.post("/parse-request")
def parse_request(body: ParseIn, ctx: CtxDep):
    s = get_settings()
    if not s.llm_configured:
        raise FeatureUnavailable(f"Describing a search in plain language needs AI. Add {get_settings().llm_key_name} to the server .env.")
    prop = ctx.property(body.property_id)
    from app.llm import gateway as llm
    from app.llm import prompts
    pid, ver, system = prompts.PARSE_REQUEST
    cur = body.current_config.model_dump(mode="json")
    user = f"Hotel: {prop.name}, {prop.locality or ''} {prop.city or ''}\nCurrent config: {json.dumps(cur)}\nRequest: {body.text}"
    out = llm.call_json(ctx=llm.CallContext(workspace_id=ctx.p.workspace_id, step="parse_request"),
                        prompt_id=pid, version=ver, system=system, user=user, tier="fast", max_output_tokens=3000)
    new = dict(cur)
    patch = []
    for p in out.get("patch", []):
        f = p.get("field")
        if f not in DiscoveryConfig.model_fields or f in ("property_id", "sources", "csv_import_id"):
            continue
        trial = {**new, f: p.get("to")}
        try:
            DiscoveryConfig.model_validate(trial)
        except Exception:  # noqa: BLE001 — drop invalid suggestions
            continue
        patch.append({"field": f, "from": new.get(f), "to": p.get("to"), "reason": str(p.get("reason", ""))[:200]})
        new = trial
    return {"patch": patch, "config": DiscoveryConfig.model_validate(new).model_dump(mode="json")}


@router.post("/jobs", status_code=202)
def create_job(body: JobIn, ctx: CtxDep):
    ctx.require_role("admin", "manager")
    cfg = body.config
    ctx.property(cfg.property_id)
    if "csv" in cfg.sources and not cfg.csv_import_id:
        raise ValidationFailed("Upload a CSV file or unselect the CSV source.")
    if cfg.csv_import_id and "csv" not in cfg.sources:
        cfg.sources.append("csv")
    if not ({"osm", "csv"} & set(cfg.sources)):
        raise ValidationFailed("Select at least one discovery source: OpenStreetMap or a CSV import.")
    active = ctx.db.execute(select(func.count()).select_from(DiscoveryJob).where(
        DiscoveryJob.property_id == cfg.property_id, DiscoveryJob.status.in_(("queued", "running", "cancelling")))).scalar_one()
    if active:
        raise Conflict("A discovery job is already running for this property. Wait for it to finish or cancel it.")
    est = estimate(ctx.db, cfg)
    j = DiscoveryJob(workspace_id=ctx.p.workspace_id, property_id=cfg.property_id, created_by=ctx.p.user_id,
                     config=cfg.model_dump(mode="json"), nl_request=body.nl_request, estimate=est, budget_usd=cfg.budget_usd)
    ctx.db.add(j)
    ctx.db.flush()
    engine.start_job(ctx.db, j, NewTask("plan"))
    ctx.db.add(JobEvent(workspace_id=ctx.p.workspace_id, job_id=j.id, level="info", stage="plan",
                        message=f"Job started by {ctx.p.full_name}. Budget cap ${cfg.budget_usd:.2f}."))
    ctx.audit("discovery.start", "discovery_job", j.id, after={"budget_usd": cfg.budget_usd})
    return {"job_id": str(j.id), "status": j.status}


@router.get("/jobs")
def list_jobs(ctx: CtxDep, property_id: UUID | None = None):
    q = select(DiscoveryJob).order_by(DiscoveryJob.created_at.desc()).limit(100)
    if property_id:
        ctx.property(property_id)
        q = q.where(DiscoveryJob.property_id == property_id)
    return [job_summary(ctx.db, j) for j in ctx.db.execute(q).scalars()]


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID, ctx: CtxDep):
    return job_detail(ctx.db, _job(ctx, job_id))


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: UUID, ctx: CtxDep):
    j = engine.lock_job(ctx.db, _job(ctx, job_id).id)
    if j.status in ("queued", "running", "paused_budget"):
        j.cancel_requested = True
        j.status = "cancelling"
        ctx.db.add(JobEvent(workspace_id=j.workspace_id, job_id=j.id, level="warning", stage=None,
                            message=f"Cancel requested by {ctx.p.full_name}. Running steps will finish first."))
        if j.status == "cancelling":
            from app.models import WorkflowTask as WT
            for t in ctx.db.execute(select(WT).where(WT.job_id == j.id, WT.status.in_(("pending", "blocked_budget")))).scalars():
                t.status = "skipped"
            ctx.db.flush()
            engine.finalize_if_done(ctx.db, j.id)
    ctx.db.flush()
    return job_detail(ctx.db, j)


@router.post("/jobs/{job_id}/resume")
def resume(job_id: UUID, body: ResumeIn, ctx: CtxDep):
    j = engine.lock_job(ctx.db, _job(ctx, job_id).id)
    if body.budget_usd:
        if body.budget_usd < float(j.spent_usd):
            raise ValidationFailed("The new budget must be at least what has already been spent.")
        j.budget_usd = body.budget_usd
    if j.status not in ("paused_budget",):
        raise Conflict("Only a job paused at its budget cap can be resumed.")
    n = engine.resume_job(ctx.db, j)
    ctx.db.add(JobEvent(workspace_id=j.workspace_id, job_id=j.id, level="info", stage=None,
                        message=f"Resumed by {ctx.p.full_name} with a ${float(j.budget_usd):.2f} cap ({n} tasks)."))
    ctx.db.flush()
    return job_detail(ctx.db, j)


@router.post("/jobs/{job_id}/retry-failed")
def retry_failed(job_id: UUID, ctx: CtxDep):
    j = engine.lock_job(ctx.db, _job(ctx, job_id).id)
    if j.status in ("running", "queued", "cancelling"):
        raise Conflict("Wait for the job to finish before retrying failed steps.")
    failed = ctx.db.execute(select(WorkflowTask).where(WorkflowTask.job_id == j.id, WorkflowTask.status == "failed")).scalars().all()
    if not failed:
        raise Conflict("There are no failed steps to retry.")
    for t in failed:
        t.status, t.attempt, t.error, t.finished_at = "pending", 0, None, None
        engine.queue.enqueue(ctx.db, t.id, j.workspace_id)
    j.status, j.finished_at, j.cancel_requested = "running", None, False
    ctx.db.add(JobEvent(workspace_id=j.workspace_id, job_id=j.id, level="info", stage=None,
                        message=f"Retrying {len(failed)} failed step(s)."))
    ctx.db.flush()
    return job_detail(ctx.db, j)


@router.get("/jobs/{job_id}/results")
def results(job_id: UUID, ctx: CtxDep, outcome: str | None = None):
    j = _job(ctx, job_id)
    q = select(DiscoveryResult).where(DiscoveryResult.job_id == j.id).order_by(DiscoveryResult.name).limit(1000)
    if outcome:
        q = q.where(DiscoveryResult.outcome == outcome)
    return [{"id": str(r.id), "name": r.name, "provider": r.provider, "outcome": r.outcome, "filter_reason": r.filter_reason,
             "company_id": str(r.company_id) if r.company_id else None, "account_id": str(r.account_id) if r.account_id else None}
            for r in ctx.db.execute(q).scalars()]
