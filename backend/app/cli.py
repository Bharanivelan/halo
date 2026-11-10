"""Admin CLI.

python -m app.cli bootstrap --workspace "Inhabitr" --email you@company.com --name "Your Name" [--password ...]
python -m app.cli add-user --email rep@company.com --name "Rep Name" --role rep [--password ...]
"""
from __future__ import annotations

import argparse
import getpass
import re
import sys

from sqlalchemy import select

from app.core.db import plain_session, tenant_session
from app.core.ids import uuid7
from app.core.security import hash_password
from app.models import Membership, ScoringModel, User, Workspace
from app.scoring.engine import DEFAULT_MODEL


def _password(arg: str | None) -> str:
    pw = arg or getpass.getpass("Password (min 10 chars): ")
    if len(pw) < 10:
        sys.exit("Password must be at least 10 characters.")
    return pw


def bootstrap(a) -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", a.workspace.lower()).strip("-")
    pw = _password(a.password)
    with plain_session() as db:
        if db.execute(select(User).where(User.email == a.email.lower())).first():
            sys.exit("A user with that email already exists.")
    ws_id = uuid7()
    with tenant_session(ws_id) as db:  # RLS: a workspace row is only writable inside its own tenant context
        db.add(Workspace(id=ws_id, name=a.workspace, slug=slug, is_demo=a.demo,
                         settings={"currency": "INR", "timezone": "Asia/Kolkata"}))
    with tenant_session(ws_id) as db:
        db.add(ScoringModel(workspace_id=ws_id, version=1, weights=DEFAULT_MODEL["weights"], params=DEFAULT_MODEL["params"],
                            notes="Initial hypothesis weights (DD-09…DD-11)"))
    with plain_session() as db:
        u = User(email=a.email.lower(), full_name=a.name, password_hash=hash_password(pw))
        db.add(u)
        db.flush()
        db.add(Membership(workspace_id=ws_id, user_id=u.id, role="admin"))
    print(f"Created workspace '{a.workspace}' and admin {a.email}.")


def add_user(a) -> None:
    pw = _password(a.password)
    with plain_session() as db:
        ws = db.execute(select(Workspace).order_by(Workspace.created_at)).scalars().first() if not a.workspace else \
            db.execute(select(Workspace).where(Workspace.slug == a.workspace)).scalar_one_or_none()
        if ws is None:
            sys.exit("Workspace not found.")
        u = db.execute(select(User).where(User.email == a.email.lower())).scalar_one_or_none()
        if u is None:
            u = User(email=a.email.lower(), full_name=a.name, password_hash=hash_password(pw))
            db.add(u)
            db.flush()
        db.add(Membership(workspace_id=ws.id, user_id=u.id, role=a.role))
    print(f"Added {a.email} as {a.role}.")


def main() -> None:
    p = argparse.ArgumentParser(prog="inhabitr")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bootstrap")
    b.add_argument("--workspace", required=True)
    b.add_argument("--email", required=True)
    b.add_argument("--name", required=True)
    b.add_argument("--password")
    b.add_argument("--demo", action="store_true")
    b.set_defaults(fn=bootstrap)
    u = sub.add_parser("add-user")
    u.add_argument("--email", required=True)
    u.add_argument("--name", required=True)
    u.add_argument("--role", choices=["admin", "manager", "rep"], default="rep")
    u.add_argument("--workspace")
    u.add_argument("--password")
    u.set_defaults(fn=add_user)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
