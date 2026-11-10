"""Database engine and session helpers.

Tenant isolation (NFR-1): every request/task that touches tenant data runs inside
`tenant_session(workspace_id)`, which sets `app.workspace_id` for the transaction.
Postgres row-level security policies compare each row's workspace_id to that setting,
so a missing or wrong setting returns no rows (fail closed).
"""
from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()
engine = create_engine(_settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def set_tenant(db: Session, workspace_id: UUID | str, user_id: UUID | str | None = None) -> None:
    db.execute(text("select set_config('app.workspace_id', :w, true)"), {"w": str(workspace_id)})
    if user_id:
        db.execute(text("select set_config('app.user_id', :u, true)"), {"u": str(user_id)})


@contextmanager
def tenant_session(workspace_id: UUID | str, user_id: UUID | str | None = None) -> Iterator[Session]:
    """A session bound to one workspace. Commits on success, rolls back on error."""
    db = SessionLocal()
    try:
        db.begin()
        set_tenant(db, workspace_id, user_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def plain_session() -> Iterator[Session]:
    """A session for global (non-tenant) tables: users, sessions, memberships, queue."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
