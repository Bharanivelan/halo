"""Row-level security: a workspace must never see another workspace's rows (NFR-1).

Requires the dev database (docker compose up -d db) with migrations applied.
"""
import pytest
from sqlalchemy import select, text

from app.core.db import SessionLocal, tenant_session
from app.core.ids import uuid7
from app.models import Company, Workspace


@pytest.fixture
def two_workspaces():
    a, b = uuid7(), uuid7()
    for ws in (a, b):
        with tenant_session(ws) as db:
            db.add(Workspace(id=ws, name=f"test-{ws}", slug=f"test-{ws}"))
            db.flush()
            db.add(Company(workspace_id=ws, name=f"Secret Co {ws}", normalized_name="secret co"))
    yield a, b
    for ws in (a, b):
        with tenant_session(ws) as db:
            db.execute(text("DELETE FROM companies WHERE workspace_id = :w"), {"w": ws})
            db.execute(text("DELETE FROM workspaces WHERE id = :w"), {"w": ws})


def test_workspace_sees_only_its_rows(two_workspaces):
    a, b = two_workspaces
    with tenant_session(a) as db:
        names = db.execute(select(Company.name).where(Company.name.like("Secret Co%"))).scalars().all()
    assert names == [f"Secret Co {a}"]


def test_no_tenant_set_sees_nothing(two_workspaces):
    db = SessionLocal()
    try:
        n = db.execute(text("SELECT count(*) FROM companies")).scalar_one()
    finally:
        db.close()
    assert n == 0


def test_cannot_write_into_other_workspace(two_workspaces):
    a, b = two_workspaces
    with pytest.raises(Exception):
        with tenant_session(a) as db:
            db.add(Company(workspace_id=b, name="Injected", normalized_name="injected"))
            db.flush()
