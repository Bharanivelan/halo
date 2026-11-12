"""Admin CLI.

python -m app.cli bootstrap --workspace "Halo" --email you@company.com --name "Your Name" [--password ...]
python -m app.cli add-user --email rep@company.com --name "Rep Name" --role rep [--password ...]
python -m app.cli rename-workspace --name "Halo" [--workspace old-slug]
python -m app.cli purge-property --name "Test Property" [--workspace slug] --yes   (permanent delete, cascades)
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
from app.models import Membership, Property, ScoringModel, User, Workspace
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
                         settings={"currency": "USD", "timezone": "America/New_York"}))
    with tenant_session(ws_id) as db:
        db.add(ScoringModel(workspace_id=ws_id, version=1, weights=DEFAULT_MODEL["weights"], params=DEFAULT_MODEL["params"],
                            notes="Initial hypothesis weights (DD-09…DD-11)"))
    with plain_session() as db:
        u = User(email=a.email.lower(), full_name=a.name, password_hash=hash_password(pw))
        db.add(u)
        db.flush()
        db.add(Membership(workspace_id=ws_id, user_id=u.id, role="admin"))
    print(f"Created workspace '{a.workspace}' and admin {a.email}.")


def _find_workspace(slug: str | None):
    """Workspaces sit behind RLS, so an unscoped session sees none. Discover ids via the global
    memberships table, then read each workspace inside its own tenant context. Oldest match wins."""
    with plain_session() as db:
        ids = db.execute(select(Membership.workspace_id).distinct()).scalars().all()
    found = []
    for wid in ids:
        with tenant_session(wid) as db:
            ws = db.get(Workspace, wid)
            if ws is not None and (slug is None or ws.slug == slug):
                found.append((ws.created_at, ws.id, ws.name))
    return min(found) if found else None


def add_user(a) -> None:
    pw = _password(a.password)
    ws = _find_workspace(a.workspace)
    if ws is None:
        sys.exit("Workspace not found.")
    _, ws_id, ws_name = ws
    with plain_session() as db:
        if db.execute(select(Membership).join(User, User.id == Membership.user_id)
                      .where(User.email == a.email.lower(), Membership.workspace_id == ws_id)).first():
            sys.exit(f"{a.email} is already a member of {ws_name}.")
        u = db.execute(select(User).where(User.email == a.email.lower())).scalar_one_or_none()
        if u is None:
            u = User(email=a.email.lower(), full_name=a.name, password_hash=hash_password(pw))
            db.add(u)
            db.flush()
        db.add(Membership(workspace_id=ws_id, user_id=u.id, role=a.role))
    print(f"Added {a.email} to {ws_name} as {a.role}.")


def rename_workspace(a) -> None:
    ws = _find_workspace(a.workspace)
    if ws is None:
        sys.exit("Workspace not found.")
    _, ws_id, old = ws
    slug = re.sub(r"[^a-z0-9]+", "-", a.name.lower()).strip("-")
    with tenant_session(ws_id) as db:
        w = db.get(Workspace, ws_id)
        w.name, w.slug = a.name, slug
    print(f"Renamed workspace '{old}' to '{a.name}' (slug {slug}).")


def purge_property(a) -> None:
    """Permanently delete a property and everything under it (accounts, runs, outreach). For test data only."""
    ws = _find_workspace(a.workspace)
    if ws is None:
        sys.exit("Workspace not found.")
    _, ws_id, _ = ws
    with tenant_session(ws_id) as db:
        props = db.execute(select(Property).where(Property.name.ilike(f"%{a.name}%"))).scalars().all()
        if not props:
            sys.exit("No matching property.")
        for p in props:
            print(f"{'Deleting' if a.yes else 'Would delete'}: {p.name} ({p.id})")
            if a.yes:
                db.delete(p)
    if not a.yes:
        print("Dry run. Re-run with --yes to delete.")


def main() -> None:
    p = argparse.ArgumentParser(prog="halo")
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
    r = sub.add_parser("rename-workspace")
    r.add_argument("--name", required=True)
    r.add_argument("--workspace")
    r.set_defaults(fn=rename_workspace)
    d = sub.add_parser("purge-property")
    d.add_argument("--name", required=True)
    d.add_argument("--workspace")
    d.add_argument("--yes", action="store_true")
    d.set_defaults(fn=purge_property)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
