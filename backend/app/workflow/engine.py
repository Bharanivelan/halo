"""Workflow engine (SYSTEM_ARCHITECTURE §7).

State lives in Postgres (`discovery_jobs`, `workflow_tasks`); the queue only says "run task X".
Each task runs one registered Step. On success the step's follow-up tasks are created and
enqueued in the same transaction, so a crash at any point leaves a resumable state.
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, ClassVar
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import tenant_session
from app.core.ids import uuid7
from app.core.logging import log
from app.models import DiscoveryJob, JobEvent, WorkflowTask
from app.workflow.budget import BudgetGuard
from app.workflow.errors import BudgetExceeded, PermanentError, TransientError
from app.workflow.queue import backoff, queue

TERMINAL = ("succeeded", "failed", "skipped")
ACTIVE = ("pending", "running", "blocked_budget")


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class NewTask:
    step: str
    subject_id: UUID | None = None
    subject_label: str | None = None
    input: dict = field(default_factory=dict)
    key_suffix: str = ""
    priority: int = 0


@dataclass
class StepContext:
    db: Session
    settings: Settings
    workspace_id: UUID
    job: DiscoveryJob
    task: WorkflowTask
    budget: BudgetGuard
    cost_usd: float = 0.0

    @property
    def job_id(self) -> UUID:
        return self.job.id

    def event(self, message: str, level: str = "info", stage: str | None = None, **data: Any) -> None:
        self.db.add(JobEvent(workspace_id=self.workspace_id, job_id=self.job.id, level=level,
                             stage=stage or STEPS[self.task.step].stage, message=message, data=data))

    def add_cost(self, usd: float) -> None:
        self.cost_usd += usd


class Step:
    name: ClassVar[str]
    stage: ClassVar[str]
    max_attempts: ClassVar[int] = 3

    def run(self, ctx: StepContext, inp: dict) -> dict:
        raise NotImplementedError

    def next(self, ctx: StepContext, output: dict) -> list[NewTask]:
        return []

    def next_on_failure(self, ctx: StepContext, error: Exception) -> list[NewTask]:
        """Follow-up tasks when this step fails permanently (e.g. still score a company whose research failed)."""
        return []

    def on_failure(self, ctx: StepContext, error: Exception) -> None:
        pass


STEPS: dict[str, Step] = {}


def step(cls: type[Step]) -> type[Step]:
    STEPS[cls.name] = cls()
    return cls


# ───────── task creation ─────────
def create_task(db: Session, job: DiscoveryJob, nt: NewTask) -> bool:
    key = f"{job.id}:{nt.step}:{nt.subject_id or '-'}:{nt.key_suffix}"
    s = STEPS[nt.step]
    stmt = insert(WorkflowTask).values(
        id=uuid7(), workspace_id=job.workspace_id,
        job_id=job.id, step=nt.step, subject_id=nt.subject_id, subject_label=nt.subject_label,
        status="pending", input=nt.input, idempotency_key=key, max_attempts=s.max_attempts,
    ).on_conflict_do_nothing(index_elements=["idempotency_key"]).returning(WorkflowTask.id)
    row = db.execute(stmt).first()
    if row:
        queue.enqueue(db, row.id, job.workspace_id, priority=nt.priority)
        return True
    return False


def lock_job(db: Session, job_id: UUID) -> DiscoveryJob:
    # FOR NO KEY UPDATE (key_share=True): inserting tasks/events takes FOR KEY SHARE on the job row via
    # the foreign key; a plain FOR UPDATE would conflict with that and deadlock concurrent finishers.
    return db.execute(select(DiscoveryJob).where(DiscoveryJob.id == job_id).with_for_update(key_share=True)).scalar_one()


def all_terminal(db: Session, job_id: UUID, step_name: str, exclude: UUID | None = None) -> bool:
    q = select(func.count()).select_from(WorkflowTask).where(
        WorkflowTask.job_id == job_id, WorkflowTask.step == step_name, WorkflowTask.status.in_(ACTIVE))
    if exclude:
        q = q.where(WorkflowTask.id != exclude)
    return db.execute(q).scalar_one() == 0


def finalize_if_done(db: Session, job_id: UUID) -> None:
    job = lock_job(db, job_id)
    if job.status not in ("running", "cancelling", "queued"):
        return
    active = db.execute(select(func.count()).select_from(WorkflowTask).where(
        WorkflowTask.job_id == job_id, WorkflowTask.status.in_(ACTIVE))).scalar_one()
    if active:
        return
    failed = db.execute(select(func.count()).select_from(WorkflowTask).where(
        WorkflowTask.job_id == job_id, WorkflowTask.status == "failed")).scalar_one()
    if job.status == "cancelling" or job.cancel_requested:
        job.status = "cancelled"
        msg = "Job cancelled. Results found so far are kept."
    elif failed:
        job.status = "completed_with_errors"
        msg = f"Finished with {failed} failed task{'s' if failed != 1 else ''}. Everything else was saved."
    else:
        job.status = "completed"
        msg = "Discovery finished."
    job.finished_at = now()
    db.add(JobEvent(workspace_id=job.workspace_id, job_id=job.id, level="info", stage=None, message=msg))


# ───────── task execution ─────────
def run_task(task_id: UUID, workspace_id: UUID) -> None:
    settings = get_settings()
    # 1) Claim: mark running (short transaction so the UI sees it).
    with tenant_session(workspace_id) as db:
        task = db.execute(select(WorkflowTask).where(WorkflowTask.id == task_id).with_for_update()).scalar_one_or_none()
        if task is None or task.status not in ("pending", "running"):
            queue.ack(task_id)
            return
        job = lock_job(db, task.job_id)
        if job.cancel_requested or job.status in ("cancelling", "cancelled"):
            task.status, task.finished_at = "skipped", now()
            finalize_if_done(db, job.id)
            queue.ack(task_id)
            return
        if job.status == "paused_budget":
            task.status = "blocked_budget"
            queue.ack(task_id)
            return
        if job.started_at and (now() - job.started_at).total_seconds() > settings.job_wall_clock_hours * 3600:
            task.status, task.finished_at = "skipped", now()
            task.error = {"class": "WallClockLimit", "message": "Job time limit reached", "retryable": False}
            if not db.execute(select(JobEvent).where(JobEvent.job_id == job.id, JobEvent.data["kind"].astext == "wall_clock")).first():
                db.add(JobEvent(workspace_id=workspace_id, job_id=job.id, level="warning", stage=None, data={"kind": "wall_clock"},
                                message=f"Time limit of {settings.job_wall_clock_hours:g} h reached; remaining steps skipped. Results so far are kept."))
            db.flush()
            finalize_if_done(db, job.id)
            queue.ack(task_id)
            return
        if job.status == "queued":
            job.status, job.started_at = "running", now()
        task.status, task.attempt, task.started_at = "running", task.attempt + 1, now()
        step_name, inp, job_id, attempt, max_attempts = task.step, dict(task.input), job.id, task.attempt, task.max_attempts

    s = STEPS[step_name]
    budget = BudgetGuard(workspace_id, job_id)
    bound = log.bind(task_id=str(task_id), job_id=str(job_id), step=step_name)
    bound.info("task_start", attempt=attempt)

    # 2) Run the step in its own transaction.
    try:
        with tenant_session(workspace_id) as db:
            task = db.get(WorkflowTask, task_id)
            job = db.get(DiscoveryJob, job_id)
            ctx = StepContext(db=db, settings=settings, workspace_id=workspace_id, job=job, task=task, budget=budget)
            output = s.run(ctx, inp)
            task.status, task.output, task.finished_at = "succeeded", output, now()
            task.cost_usd = ctx.cost_usd
            for nt in s.next(ctx, output):
                create_task(db, job, nt)
            db.flush()
            finalize_if_done(db, job_id)
        queue.ack(task_id)
        bound.info("task_ok")
        return
    except BudgetExceeded as e:
        with tenant_session(workspace_id) as db:
            task = db.get(WorkflowTask, task_id)
            task.status, task.attempt = "blocked_budget", max(0, task.attempt - 1)
            job = lock_job(db, job_id)
            if job.status == "running":
                job.status = "paused_budget"
                db.add(JobEvent(workspace_id=workspace_id, job_id=job_id, level="warning", stage=s.stage,
                                message=f"Paused at the budget cap. {e}. Raise the cap to continue, or finish with partial results."))
        queue.ack(task_id)
        bound.warning("task_budget_blocked")
        return
    except Exception as e:  # noqa: BLE001 — classified below
        if isinstance(e, OperationalError):  # deadlocks / serialization failures / dropped connections are transient
            e = TransientError(f"Database busy ({type(getattr(e, 'orig', e)).__name__}); retrying")
        retryable = isinstance(e, TransientError) and attempt < max_attempts
        user_msg = str(e) if isinstance(e, (TransientError, PermanentError)) else "Unexpected error (logged for the developer)."
        if not isinstance(e, (TransientError, PermanentError)):
            bound.error("task_crash", error=repr(e), tb=traceback.format_exc()[-4000:])
        else:
            bound.warning("task_error", error=str(e), retryable=retryable)
        with tenant_session(workspace_id) as db:
            task = db.get(WorkflowTask, task_id)
            job = db.get(DiscoveryJob, job_id)
            task.error = {"class": type(e).__name__, "message": user_msg, "retryable": retryable}
            if retryable:
                task.status = "pending"
                retry_at = backoff(attempt, getattr(e, "retry_after_s", None))
                db.flush()
                queue.nack(task_id, retry_at=retry_at)
                return
            task.status, task.finished_at = "failed", now()
            ctx = StepContext(db=db, settings=settings, workspace_id=workspace_id, job=job, task=task, budget=budget)
            label = task.subject_label or ""
            ctx.event(f"{s_label(step_name)} failed{(' for ' + label) if label else ''}: {user_msg}", level="error")
            try:
                s.on_failure(ctx, e)
                for nt in s.next_on_failure(ctx, e):
                    create_task(db, job, nt)
            except Exception:  # noqa: BLE001
                bound.error("on_failure_crash", tb=traceback.format_exc()[-2000:])
            db.flush()
            finalize_if_done(db, job_id)
        queue.ack(task_id)


def s_label(step_name: str) -> str:
    return {"plan": "Planning", "discover_osm": "OpenStreetMap discovery", "discover_search": "Web search discovery",
            "discover_csv": "CSV import", "resolve": "De-duplication", "classify": "Classification",
            "research": "Research", "signals": "Signal detection", "score": "Scoring"}.get(step_name, step_name)


# ───────── job control ─────────
def start_job(db: Session, job: DiscoveryJob, first: NewTask) -> None:
    create_task(db, job, first)


def resume_job(db: Session, job: DiscoveryJob, include_failed: bool = False) -> int:
    statuses = ["blocked_budget", "pending"] + (["failed"] if include_failed else [])
    tasks = db.execute(select(WorkflowTask).where(WorkflowTask.job_id == job.id, WorkflowTask.status.in_(statuses))).scalars().all()
    for t in tasks:
        if t.status == "failed":
            t.attempt = 0
            t.error = None
        t.status = "pending"
        queue.enqueue(db, t.id, job.workspace_id)
    if tasks and job.status in ("paused_budget", "completed", "completed_with_errors"):
        job.status, job.finished_at = "running", None
    return len(tasks)


def stage_counts(db: Session, job_id: UUID) -> dict[str, dict[str, int]]:
    rows = db.execute(text(
        "SELECT step, status, count(*) AS n FROM workflow_tasks WHERE job_id = :j GROUP BY step, status"), {"j": job_id}).all()
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        st = STEPS[r.step].stage if r.step in STEPS else r.step
        d = out.setdefault(st, {"pending": 0, "running": 0, "succeeded": 0, "failed": 0, "skipped": 0})
        key = "pending" if r.status == "blocked_budget" else r.status
        d[key] = d.get(key, 0) + r.n
    return out


Callback = Callable[[], None]
