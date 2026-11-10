"""Per-job budget enforcement (NFR-6, AGENT_ARCHITECTURE §9.3).

reserve() before every paid call, commit() after. Both run in their own short
transactions so concurrent workers always see the latest spend.
"""
from uuid import UUID

from sqlalchemy import text

from app.core.db import tenant_session
from app.workflow.errors import BudgetExceeded


class BudgetGuard:
    def __init__(self, workspace_id: UUID, job_id: UUID):
        self.workspace_id = workspace_id
        self.job_id = job_id

    def reserve(self, estimate_usd: float) -> None:
        with tenant_session(self.workspace_id) as db:
            ok = db.execute(
                text(
                    "UPDATE discovery_jobs SET reserved_usd = reserved_usd + :e "
                    "WHERE id = :j AND spent_usd + reserved_usd + :e <= budget_usd RETURNING id"
                ),
                {"e": estimate_usd, "j": self.job_id},
            ).first()
        if not ok:
            raise BudgetExceeded(f"Budget cap reached (next call ≈ ${estimate_usd:.4f})")

    def commit(self, estimate_usd: float, actual_usd: float) -> None:
        with tenant_session(self.workspace_id) as db:
            db.execute(
                text(
                    "UPDATE discovery_jobs SET reserved_usd = GREATEST(reserved_usd - :e, 0), "
                    "spent_usd = spent_usd + :a WHERE id = :j"
                ),
                {"e": estimate_usd, "a": actual_usd, "j": self.job_id},
            )
