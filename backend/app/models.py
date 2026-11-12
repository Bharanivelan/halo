"""SQLAlchemy models. Schema reference: docs/DATABASE_SCHEMA.md.

Tables marked TENANT carry workspace_id and are protected by row-level security
(see migrations). Global tables: users, memberships, sessions, auth_tokens, queue_items,
industries, worker_heartbeats.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer,
    LargeBinary, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.ids import uuid7


class Base(DeclarativeBase):
    pass


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)


def ws_fk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)


def created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def updated() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


def check_in(col: str, values: list[str], name: str) -> CheckConstraint:
    vals = ",".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{col} IN ({vals})", name=name)


TENANT_TABLES = [
    "workspaces", "property_access", "properties", "property_offerings", "property_target_profiles", "companies",
    "company_locations", "company_identifiers", "sources", "claims", "signals", "accounts",
    "scoring_models", "account_scores", "target_role_recommendations", "contacts",
    "discovery_jobs", "discovery_results", "workflow_tasks", "job_events", "llm_calls",
    "provider_calls", "copilot_outputs", "opportunities", "activities", "csv_imports", "audit_logs",
]
DATA_ORIGIN = ["real", "mock", "manual"]


# ───────── Identity ─────────
class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = pk()
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"), check_in("role", ["admin", "manager", "rep"], "ck_membership_role"))
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created()


class PropertyAccess(Base):
    __tablename__ = "property_access"
    __table_args__ = (UniqueConstraint("membership_id", "property_id"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    membership_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="CASCADE"))
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"))


class SessionRow(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = pk()
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    membership_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="CASCADE"))
    csrf_token: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = created()
    last_seen_at: Mapped[datetime] = created()
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(300), index=True)
    success: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = created()


# ───────── Properties ─────────
class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (check_in("lifecycle", ["pre_opening", "operating"], "ck_property_lifecycle"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(120))
    address_line: Mapped[str | None] = mapped_column(String(300))
    locality: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="US")
    location = mapped_column(Geography("POINT", srid=4326, spatial_index=True))
    lifecycle: Mapped[str] = mapped_column(String(20), default="pre_opening")
    opening_date: Mapped[date | None] = mapped_column(Date)
    rooms_count: Mapped[int | None] = mapped_column(Integer)
    meeting_rooms_count: Mapped[int | None] = mapped_column(Integer)
    largest_meeting_capacity: Mapped[int | None] = mapped_column(Integer)
    banquet_capacity: Mapped[int | None] = mapped_column(Integer)
    restaurants_count: Mapped[int | None] = mapped_column(Integer)
    facilities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    description: Mapped[str | None] = mapped_column(Text)
    is_hypothetical: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class PropertyOffering(Base):
    __tablename__ = "property_offerings"
    __table_args__ = (UniqueConstraint("property_id", "offering"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    offering: Mapped[str] = mapped_column(String(30))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)


class PropertyTargetProfile(Base):
    __tablename__ = "property_target_profiles"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), unique=True)
    radius_km: Mapped[float] = mapped_column(Float, default=15)
    industries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    employee_min: Mapped[int | None] = mapped_column(Integer)
    employee_max: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


# ───────── Companies & evidence ─────────
class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        check_in("data_origin", DATA_ORIGIN, "ck_company_origin"),
        check_in("research_status", ["not_researched", "researching", "researched", "failed"], "ck_company_research"),
        Index("ix_companies_ws_norm", "workspace_id", "normalized_name"),
    )
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    name: Mapped[str] = mapped_column(String(300))
    normalized_name: Mapped[str] = mapped_column(String(300))
    primary_domain: Mapped[str | None] = mapped_column(String(255), index=True)
    website: Mapped[str | None] = mapped_column(String(500))
    industry_code: Mapped[str | None] = mapped_column(String(50))
    employee_range: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    hq_city: Mapped[str | None] = mapped_column(String(120))
    hq_country: Mapped[str | None] = mapped_column(String(80))
    data_origin: Mapped[str] = mapped_column(String(10), default="real")
    research_status: Mapped[str] = mapped_column(String(20), default="not_researched")
    research_note: Mapped[str | None] = mapped_column(Text)
    last_researched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class CompanyLocation(Base):
    __tablename__ = "company_locations"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    label: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500))
    locality: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120))
    location = mapped_column(Geography("POINT", srid=4326, spatial_index=True), nullable=True)
    location_type: Mapped[str] = mapped_column(String(30), default="unknown")
    is_primary_local: Mapped[bool] = mapped_column(Boolean, default=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created()


class CompanyIdentifier(Base):
    __tablename__ = "company_identifiers"
    __table_args__ = (UniqueConstraint("workspace_id", "kind", "value"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(String(500))


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    url: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(Integer)
    license_tag: Mapped[str] = mapped_column(String(40), default="public_web")
    exportable: Mapped[bool] = mapped_column(Boolean, default=True)
    data_origin: Mapped[str] = mapped_column(String(10), default="real")
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = created()


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        check_in("kind", ["fact", "inference", "unknown"], "ck_claim_kind"),
        CheckConstraint(
            "kind <> 'fact' OR (source_id IS NOT NULL AND evidence_quote IS NOT NULL "
            "AND grounding_status IN ('passed','passed_fuzzy'))",
            name="ck_claim_fact_grounded",
        ),
        Index("ix_claims_current", "company_id", "field", postgresql_where="is_current"),
    )
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(50))
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    kind: Mapped[str] = mapped_column(String(12))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"))
    evidence_quote: Mapped[str | None] = mapped_column(Text)
    supports: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    rationale: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    grounding_status: Mapped[str] = mapped_column(String(20), default="not_applicable")
    grounding_detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    observed_at: Mapped[datetime] = created()
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    produced_by_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    data_origin: Mapped[str] = mapped_column(String(10), default="real")
    created_at: Mapped[datetime] = created()


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint("company_id", "signal_type", "source_id"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    signal_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"))
    evidence_quote: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime] = created()
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    implied_offerings: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    recommended_approach: Mapped[str | None] = mapped_column(Text)
    grounding_status: Mapped[str] = mapped_column(String(20), default="not_applicable")
    produced_by_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    data_origin: Mapped[str] = mapped_column(String(10), default="real")


# ───────── Accounts & scoring ─────────
ACCOUNT_STATUSES = ["discovered", "qualified", "contact_identified", "outreach_prepared", "outreach_sent", "engaged", "dismissed"]


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("property_id", "company_id"),
        check_in("status", ACCOUNT_STATUSES, "ck_account_status"),
        Index("ix_accounts_rank", "property_id", "priority"),
    )
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="discovered")
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="SET NULL"))
    dismissed_reason: Mapped[str | None] = mapped_column(String(40))
    dismissed_note: Mapped[str | None] = mapped_column(Text)
    distance_km: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[float | None] = mapped_column(Float)
    tier: Mapped[str | None] = mapped_column(String(1))
    fit: Mapped[int | None] = mapped_column(Integer)
    intent: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[int | None] = mapped_column(Integer)
    actionability: Mapped[str] = mapped_column(String(30), default="none")
    current_score_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    first_seen_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class ScoringModel(Base):
    __tablename__ = "scoring_models"
    __table_args__ = (UniqueConstraint("workspace_id", "version"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    version: Mapped[int] = mapped_column(Integer)
    weights: Mapped[dict] = mapped_column(JSONB)
    params: Mapped[dict] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created()


class AccountScore(Base):
    __tablename__ = "account_scores"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    scoring_model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scoring_models.id"))
    model_version: Mapped[int] = mapped_column(Integer)
    fit: Mapped[int] = mapped_column(Integer)
    intent: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[int] = mapped_column(Integer)
    actionability: Mapped[str] = mapped_column(String(30))
    priority: Mapped[float] = mapped_column(Float)
    tier: Mapped[str] = mapped_column(String(1))
    breakdown: Mapped[dict] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = created()
    computed_by_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class TargetRoleRecommendation(Base):
    __tablename__ = "target_role_recommendations"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    role_code: Mapped[str] = mapped_column(String(40))
    offering: Mapped[str] = mapped_column(String(30))
    rank: Mapped[int] = mapped_column(Integer)
    rationale: Mapped[str] = mapped_column(Text)


# ───────── Contacts ─────────
class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(200))
    role_code: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    profile_url: Mapped[str | None] = mapped_column(String(500))
    source_note: Mapped[str] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    data_origin: Mapped[str] = mapped_column(String(10), default="manual")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


# ───────── Discovery & workflow ─────────
JOB_STATUSES = ["queued", "running", "paused_budget", "completed", "completed_with_errors", "failed", "cancelling", "cancelled"]
TASK_STATUSES = ["pending", "running", "succeeded", "failed", "skipped", "blocked_budget"]


class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"
    __table_args__ = (check_in("status", JOB_STATUSES, "ck_job_status"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(20), default="discovery")  # discovery | refresh
    status: Mapped[str] = mapped_column(String(30), default="queued")
    config: Mapped[dict] = mapped_column(JSONB)
    nl_request: Mapped[str | None] = mapped_column(Text)
    estimate: Mapped[dict | None] = mapped_column(JSONB)
    budget_usd: Mapped[float] = mapped_column(Numeric(10, 4))
    spent_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    reserved_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class DiscoveryResult(Base):
    __tablename__ = "discovery_results"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("discovery_jobs.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(300))
    raw: Mapped[dict] = mapped_column(JSONB)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    outcome: Mapped[str] = mapped_column(String(20), default="new")
    filter_reason: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = created()


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    __table_args__ = (check_in("status", TASK_STATUSES, "ck_task_status"), Index("ix_tasks_job_status", "job_id", "status"))
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("discovery_jobs.id", ondelete="CASCADE"))
    step: Mapped[str] = mapped_column(String(40))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    subject_label: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[dict | None] = mapped_column(JSONB)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    idempotency_key: Mapped[str] = mapped_column(String(300), unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class QueueItem(Base):
    """Owned by PostgresQueueBackend. Global (not RLS) so workers can claim before knowing the tenant."""
    __tablename__ = "queue_items"
    __table_args__ = (Index("ix_queue_ready", "run_after", "priority"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    leased_by: Mapped[str | None] = mapped_column(String(100))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enqueued_at: Mapped[datetime] = created()


class JobEvent(Base):
    __tablename__ = "job_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("discovery_jobs.id", ondelete="CASCADE"), index=True)
    level: Mapped[str] = mapped_column(String(10), default="info")
    stage: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created()


class LlmCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    step: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(60))
    prompt_id: Mapped[str] = mapped_column(String(60))
    prompt_version: Mapped[str] = mapped_column(String(20))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="ok")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created()


class ProviderCall(Base):
    __tablename__ = "provider_calls"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    provider: Mapped[str] = mapped_column(String(30))
    operation: Mapped[str] = mapped_column(String(40))
    units: Mapped[int] = mapped_column(Integer, default=1)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    status: Mapped[str] = mapped_column(String(10), default="ok")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = created()


# ───────── Copilot & pipeline ─────────
class CopilotOutput(Base):
    __tablename__ = "copilot_outputs"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"))
    offering: Mapped[str] = mapped_column(String(30))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSONB)
    edited: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="generated")
    generated_by: Mapped[str] = mapped_column(String(10), default="llm")
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (check_in("stage", ["interested", "meeting_scheduled", "negotiation", "won", "lost"], "ck_opp_stage"),)
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    offering: Mapped[str] = mapped_column(String(30))
    stage: Mapped[str] = mapped_column(String(30), default="interested")
    value_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    probability: Mapped[int | None] = mapped_column(Integer)
    owner_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="SET NULL"))
    loss_reason: Mapped[str | None] = mapped_column(String(40))
    loss_note: Mapped[str | None] = mapped_column(Text)
    won_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class ActivityRow(Base):
    __tablename__ = "activities"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(String(30))
    body: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = created()
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class CsvImport(Base):
    __tablename__ = "csv_imports"
    id: Mapped[uuid.UUID] = pk()
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="parsed")
    mapping: Mapped[dict] = mapped_column(JSONB, default=dict)
    rows: Mapped[list] = mapped_column(JSONB, default=list)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = created()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[uuid.UUID] = ws_fk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = created()
