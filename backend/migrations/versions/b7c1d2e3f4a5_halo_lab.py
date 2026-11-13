"""Halo Lab (D-47): lead/signal ratings, agent versions, lessons.

Revision ID: b7c1d2e3f4a5
Revises: 8aff8ecf4176
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7c1d2e3f4a5"
down_revision = "8aff8ecf4176"
branch_labels = None
depends_on = None

TABLES = ["lead_feedback", "signal_feedback", "agent_versions", "lab_lessons"]


def _ws():
    return sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)


def _now(name):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "lead_feedback",
        sa.Column("id", sa.UUID(), primary_key=True), _ws(),
        sa.Column("account_id", sa.UUID(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.UUID(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(40)), sa.Column("note", sa.Text()),
        sa.Column("source", sa.String(10), nullable=False, server_default="app"),
        sa.Column("created_by_membership_id", sa.UUID(), sa.ForeignKey("memberships.id", ondelete="SET NULL")),
        _now("created_at"), _now("updated_at"),
        sa.UniqueConstraint("account_id", name="uq_lead_feedback_account"),
        sa.CheckConstraint("verdict IN ('good_fit','not_fit')", name="ck_lead_feedback_verdict"),
        sa.CheckConstraint("source IN ('app','csv')", name="ck_lead_feedback_source"),
    )
    op.create_table(
        "signal_feedback",
        sa.Column("id", sa.UUID(), primary_key=True), _ws(),
        sa.Column("signal_id", sa.UUID(), sa.ForeignKey("signals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("verdict", sa.String(10), nullable=False), sa.Column("note", sa.Text()),
        sa.Column("created_by_membership_id", sa.UUID(), sa.ForeignKey("memberships.id", ondelete="SET NULL")),
        _now("created_at"), _now("updated_at"),
        sa.UniqueConstraint("signal_id", name="uq_signal_feedback_signal"),
        sa.CheckConstraint("verdict IN ('correct','wrong')", name="ck_signal_feedback_verdict"),
    )
    op.create_table(
        "agent_versions",
        sa.Column("id", sa.UUID(), primary_key=True), _ws(),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="candidate"),
        sa.Column("parent_version", sa.Integer()),
        sa.Column("harness", postgresql.JSONB(), nullable=False),
        sa.Column("changes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary", sa.Text()),
        sa.Column("lab_job_id", sa.UUID(), sa.ForeignKey("discovery_jobs.id", ondelete="SET NULL")),
        sa.Column("created_by", sa.UUID()), sa.Column("decided_by", sa.UUID()),
        sa.Column("decided_at", sa.DateTime(timezone=True)), _now("created_at"),
        sa.UniqueConstraint("workspace_id", "version", name="uq_agent_versions_ws_version"),
        sa.CheckConstraint("status IN ('active','candidate','retired','rejected')", name="ck_agent_version_status"),
    )
    op.create_table(
        "lab_lessons",
        sa.Column("id", sa.UUID(), primary_key=True), _ws(),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("lab_job_id", sa.UUID(), sa.ForeignKey("discovery_jobs.id", ondelete="SET NULL")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _now("created_at"),
    )
    for t in TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {t} USING (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid) "
                   f"WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid)")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {t} TO inhabitr_app")


def downgrade() -> None:
    for t in reversed(TABLES):
        op.drop_table(t)
