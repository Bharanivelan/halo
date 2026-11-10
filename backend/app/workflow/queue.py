"""Queue abstraction (P-02).

The workflow engine only talks to `QueueBackend`. The MVP implementation stores queue
items in Postgres and claims them with `FOR UPDATE SKIP LOCKED`, so enqueueing happens
in the SAME transaction as the domain write that created the task (no dual-write bugs).
Swapping to Celery/Temporal later means writing another class with this interface.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import plain_session


class QueueBackend(Protocol):
    def enqueue(self, db: Session, task_id: UUID, workspace_id: UUID, *, run_after: datetime | None = None, priority: int = 0) -> None: ...
    def claim(self, worker_id: str, limit: int) -> list[tuple[UUID, UUID]]: ...
    def heartbeat(self, task_ids: list[UUID], worker_id: str) -> None: ...
    def ack(self, task_id: UUID) -> None: ...
    def nack(self, task_id: UUID, *, retry_at: datetime) -> None: ...


class PostgresQueueBackend:
    def __init__(self) -> None:
        self.lease = get_settings().task_lease_seconds

    def enqueue(self, db, task_id, workspace_id, *, run_after=None, priority=0):
        db.execute(
            text(
                "INSERT INTO queue_items (task_id, workspace_id, priority, run_after) "
                "VALUES (:t, :w, :p, COALESCE(:ra, now())) "
                "ON CONFLICT (task_id) DO UPDATE SET run_after = EXCLUDED.run_after, leased_by = NULL, lease_expires_at = NULL"
            ),
            {"t": task_id, "w": workspace_id, "p": priority, "ra": run_after},
        )

    def claim(self, worker_id, limit):
        with plain_session() as db:
            rows = db.execute(
                text(
                    """
                    UPDATE queue_items SET leased_by = :wid, lease_expires_at = now() + make_interval(secs => :lease)
                    WHERE id IN (
                        SELECT id FROM queue_items
                        WHERE run_after <= now() AND (leased_by IS NULL OR lease_expires_at < now())
                        ORDER BY priority DESC, id
                        LIMIT :n FOR UPDATE SKIP LOCKED)
                    RETURNING task_id, workspace_id
                    """
                ),
                {"wid": worker_id, "lease": self.lease, "n": limit},
            ).all()
        return [(r.task_id, r.workspace_id) for r in rows]

    def heartbeat(self, task_ids, worker_id):
        if not task_ids:
            return
        with plain_session() as db:
            db.execute(
                text("UPDATE queue_items SET lease_expires_at = now() + make_interval(secs => :lease) "
                     "WHERE task_id = ANY(:ids) AND leased_by = :wid"),
                {"lease": self.lease, "ids": list(task_ids), "wid": worker_id},
            )

    def ack(self, task_id):
        with plain_session() as db:
            db.execute(text("DELETE FROM queue_items WHERE task_id = :t"), {"t": task_id})

    def nack(self, task_id, *, retry_at):
        with plain_session() as db:
            db.execute(
                text("UPDATE queue_items SET leased_by = NULL, lease_expires_at = NULL, run_after = :ra WHERE task_id = :t"),
                {"ra": retry_at, "t": task_id},
            )


queue: QueueBackend = PostgresQueueBackend()


def backoff(attempt: int, retry_after_s: float | None = None) -> datetime:
    delay = retry_after_s if retry_after_s else min(300, 5 * (2 ** max(0, attempt - 1)))
    return datetime.now(timezone.utc) + timedelta(seconds=delay)
