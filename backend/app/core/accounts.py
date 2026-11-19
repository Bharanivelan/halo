"""Creating a workspace with its first admin. Used by sign-up (D-51) and `app.cli bootstrap`."""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.core.db import plain_session, tenant_session
from app.core.ids import uuid7
from app.core.security import hash_password
from app.models import Membership, ScoringModel, User, Workspace
from app.scoring.engine import DEFAULT_MODEL


class EmailTaken(Exception):
    pass


@dataclass
class NewAccount:
    workspace_id: UUID
    user_id: UUID
    membership_id: UUID


def _slug(name: str, unique_suffix: bool) -> str:
    # Workspaces are hidden from each other by row-level security, so "is this slug taken?" can't be asked
    # from here; self-service sign-ups add a random suffix instead.
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80] or "workspace"
    return f"{base}-{secrets.token_hex(4)}" if unique_suffix else base


def create_workspace_with_admin(*, workspace_name: str, email: str, full_name: str, password: str,
                                is_demo: bool = False, unique_slug: bool = False) -> NewAccount:
    """New workspace (with the default scoring model) and its admin user. Raises EmailTaken."""
    email = email.strip().lower()
    with plain_session() as db:
        if db.execute(select(User.id).where(User.email == email)).first():
            raise EmailTaken(email)
    ws_id = uuid7()
    with tenant_session(ws_id) as db:  # RLS: a workspace row is only writable inside its own tenant context
        db.add(Workspace(id=ws_id, name=workspace_name, slug=_slug(workspace_name, unique_slug), is_demo=is_demo,
                         settings={"currency": "USD", "timezone": "America/New_York"}))
    with tenant_session(ws_id) as db:
        db.add(ScoringModel(workspace_id=ws_id, version=1, weights=DEFAULT_MODEL["weights"], params=DEFAULT_MODEL["params"],
                            notes="Initial hypothesis weights (DD-09…DD-11)"))
    with plain_session() as db:
        u = User(email=email, full_name=full_name.strip(), password_hash=hash_password(password))
        db.add(u)
        db.flush()
        m = Membership(workspace_id=ws_id, user_id=u.id, role="admin")
        db.add(m)
        db.flush()
        return NewAccount(workspace_id=ws_id, user_id=u.id, membership_id=m.id)
