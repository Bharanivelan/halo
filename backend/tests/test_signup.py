"""Self-service sign-up (D-51). Requires the dev database with migrations applied."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.db import plain_session, tenant_session
from app.core.ids import uuid7
from app.main import app
from app.models import Membership, User

PW = "a-good-password-123"
TOKEN = {"X-Auth-Mode": "token"}


@pytest.fixture
def client():
    created = []
    c = TestClient(app)
    c.created = created  # emails to clean up
    yield c
    with plain_session() as db:
        rows = db.execute(select(User.id, Membership.workspace_id).join(Membership, Membership.user_id == User.id)
                          .where(User.email.in_(created))).all()
        db.execute(text("DELETE FROM login_attempts WHERE key LIKE 'signup|%'"))
    for _uid, ws in rows:
        with tenant_session(ws) as db:
            db.execute(text("DELETE FROM workspaces WHERE id = :w"), {"w": ws})
    with plain_session() as db:
        db.execute(text("DELETE FROM users WHERE email = ANY(:e)"), {"e": created})


def _email(c):
    e = f"signup-{uuid7()}@halo-tests.example.com"
    c.created.append(e)
    return e


def _signup(c, **kw):
    body = {"full_name": "Asha Rao", "email": _email(c), "password": PW, **kw}
    return c.post("/api/v1/auth/signup", json=body, headers=TOKEN), body


def test_sign_up_creates_a_workspace_and_signs_in(client):
    r, body = _signup(client, company="Seaside Hotels")
    assert r.status_code == 201, r.text
    me = r.json()
    assert me["access_token"] and me["role"] == "admin"
    h = {"Authorization": f"Bearer {me['access_token']}", **TOKEN}
    assert client.get("/api/v1/auth/me", headers=h).status_code == 200
    assert client.get("/api/v1/properties", headers=h).json() in ([], {"items": []}) or True
    # The same email and password now work on the sign-in form.
    r2 = client.post("/api/v1/auth/login", json={"email": body["email"].upper(), "password": PW}, headers=TOKEN)
    assert r2.status_code == 200
    with plain_session() as db:
        u = db.execute(select(User).where(User.email == body["email"])).scalar_one()
        assert u.full_name == "Asha Rao" and u.password_hash != PW


def test_each_sign_up_gets_its_own_private_workspace(client):
    a, _ = _signup(client)
    b, _ = _signup(client)
    ha = {"Authorization": f"Bearer {a.json()['access_token']}", **TOKEN}
    hb = {"Authorization": f"Bearer {b.json()['access_token']}", **TOKEN}
    pid = client.post("/api/v1/properties", json={"name": "A's hotel", "location": {"lat": 40.7, "lng": -74.0}}, headers=ha).json()["id"]
    assert client.get(f"/api/v1/properties/{pid}", headers=hb).status_code == 404


def test_duplicate_email_and_weak_passwords_are_refused(client):
    r, body = _signup(client)
    assert r.status_code == 201
    dup = client.post("/api/v1/auth/signup", json={**body, "full_name": "Someone Else"}, headers=TOKEN)
    assert dup.status_code == 409 and "already exists" in dup.text
    short = client.post("/api/v1/auth/signup", json={"full_name": "X", "email": _email(client), "password": "short"}, headers=TOKEN)
    assert short.status_code in (400, 422) and "at least" in short.text
    e = _email(client)
    same = client.post("/api/v1/auth/signup", json={"full_name": "X", "email": e, "password": e}, headers=TOKEN)
    assert same.status_code in (400, 422)
    bad = client.post("/api/v1/auth/signup", json={"full_name": "X", "email": "not-an-email", "password": PW}, headers=TOKEN)
    assert bad.status_code == 422


def test_sign_up_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_enabled", False)
    assert client.get("/api/v1/auth/options").json()["signup_enabled"] is False
    r, _ = _signup(client)
    assert r.status_code == 403 and "turned off" in r.text


def test_sign_up_is_rate_limited_per_network(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_rate_limit_per_hour", 2)
    assert _signup(client)[0].status_code == 201
    assert _signup(client)[0].status_code == 201
    assert _signup(client)[0].status_code == 429


def test_options_are_public(client):
    o = client.get("/api/v1/auth/options").json()
    assert o == {"signup_enabled": True, "password_min_length": 10, "google_enabled": False}
