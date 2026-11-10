"""Request dependencies: authentication, CSRF, tenant-scoped DB session, permissions (SYSTEM_ARCHITECTURE §4–6)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Iterator
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal, plain_session, set_tenant
from app.core.errors import Forbidden, NotFound, Unauthenticated
from app.core.security import hash_token
from app.models import AuditLog, Property, PropertyAccess

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class Principal:
    user_id: UUID
    workspace_id: UUID
    membership_id: UUID
    role: str
    session_id: UUID
    csrf_token: str
    full_name: str
    email: str


def get_principal(request: Request) -> Principal:
    s = get_settings()
    # Bearer token (separate frontend, D-36) or session cookie (same-site frontend).
    auth = request.headers.get("Authorization", "")
    bearer = auth[7:].strip() if s.token_auth_enabled and auth[:7].lower() == "bearer " else ""
    token = bearer or request.cookies.get(s.session_cookie_name)
    if not token:
        raise Unauthenticated()
    with plain_session() as db:
        row = db.execute(text(
            """SELECT s.id, s.user_id, s.workspace_id, s.membership_id, s.csrf_token, s.last_seen_at,
                      m.role, u.full_name, u.email
               FROM sessions s JOIN users u ON u.id = s.user_id JOIN memberships m ON m.id = s.membership_id
               WHERE s.token_hash = :h AND s.revoked_at IS NULL AND s.idle_expires_at > now()
                 AND s.absolute_expires_at > now() AND u.is_active AND m.is_active"""), {"h": hash_token(token)}).first()
        if row is None:
            raise Unauthenticated()
        now = datetime.now(timezone.utc)
        if now - row.last_seen_at > timedelta(minutes=5):
            db.execute(text("UPDATE sessions SET last_seen_at = now(), idle_expires_at = now() + make_interval(days => :d) "
                            "WHERE id = :id"), {"d": s.session_idle_days, "id": row.id})
    p = Principal(user_id=row.user_id, workspace_id=row.workspace_id, membership_id=row.membership_id, role=row.role,
                  session_id=row.id, csrf_token=row.csrf_token, full_name=row.full_name, email=row.email)
    # CSRF only applies to cookie auth: a bearer token is never sent automatically by the browser.
    if not bearer and request.method not in SAFE_METHODS and request.headers.get("X-CSRF-Token") != p.csrf_token:
        raise Forbidden("Missing or invalid CSRF token. Reload the page and try again.")
    request.state.principal = p
    return p


class Ctx:
    """Everything an endpoint needs: who is calling and a DB session scoped to their workspace."""

    def __init__(self, p: Principal, db: Session, request: Request):
        self.p, self.db, self.request = p, db, request

    def audit(self, action: str, entity_type: str | None = None, entity_id=None, before=None, after=None) -> None:
        self.db.add(AuditLog(workspace_id=self.p.workspace_id, actor_user_id=self.p.user_id, action=action,
                             entity_type=entity_type, entity_id=str(entity_id) if entity_id else None, before=before,
                             after=after, request_id=getattr(self.request.state, "request_id", None)))

    def require_role(self, *roles: str) -> None:
        if self.p.role not in roles:
            raise Forbidden("Your role doesn't allow this action.")

    def property(self, property_id: UUID) -> Property:
        prop = self.db.get(Property, property_id)
        if prop is None or prop.archived_at is not None:
            raise NotFound("Property not found")
        if self.p.role == "rep":
            ok = self.db.execute(select(PropertyAccess).where(PropertyAccess.membership_id == self.p.membership_id,
                                                              PropertyAccess.property_id == property_id)).first()
            if not ok:
                raise NotFound("Property not found")  # DD-05: don't reveal existence
        return prop

    def accessible_property_ids(self) -> list[UUID] | None:
        """None = all properties in the workspace."""
        if self.p.role != "rep":
            return None
        return list(self.db.execute(select(PropertyAccess.property_id).where(
            PropertyAccess.membership_id == self.p.membership_id)).scalars())


def get_ctx(request: Request, p: Annotated[Principal, Depends(get_principal)]) -> Iterator[Ctx]:
    db = SessionLocal()
    try:
        db.begin()
        set_tenant(db, p.workspace_id, p.user_id)
        yield Ctx(p, db, request)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


CtxDep = Annotated[Ctx, Depends(get_ctx)]
