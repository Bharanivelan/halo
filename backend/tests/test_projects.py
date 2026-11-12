"""Projects flow (D-38…D-40): one project = one hotel, US default with US/India choice, auto-start, soft delete.

Requires the dev database (docker compose up -d db) with migrations applied. No network calls.
Stop the worker (python -m app.worker) first: these tests queue real runs, and a live worker would pick them up.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.db import plain_session, tenant_session
from app.core.ids import uuid7
from app.core.security import hash_password
from app.main import app
from app.models import Membership, User, WorkflowTask, Workspace

PW = "test-password-123"
HOTEL = {"name": "Test Hotel", "location": {"lat": 40.7128, "lng": -74.0060}}


def _make_user(ws_id, role):
    email = f"{role}-{ws_id}@halo-tests.example.com"
    with plain_session() as db:
        u = User(email=email, full_name=f"Test {role}", password_hash=hash_password(PW))
        db.add(u)
        db.flush()
        db.add(Membership(workspace_id=ws_id, user_id=u.id, role=role))
    return email


def _login(client, email):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PW}, headers={"X-Auth-Mode": "token"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Auth-Mode": "token"}


@pytest.fixture
def ws():
    ws_id = uuid7()
    with tenant_session(ws_id) as db:
        db.add(Workspace(id=ws_id, name=f"test-{ws_id}", slug=f"test-{ws_id}"))
    emails = {"manager": _make_user(ws_id, "manager"), "rep": _make_user(ws_id, "rep")}
    client = TestClient(app)
    yield ws_id, client, {k: _login(client, v) for k, v in emails.items()}
    with tenant_session(ws_id) as db:
        task_ids = db.execute(select(WorkflowTask.id)).scalars().all()
    with plain_session() as db:
        if task_ids:
            db.execute(text("DELETE FROM queue_items WHERE task_id = ANY(:ids)"), {"ids": task_ids})
        db.execute(text("DELETE FROM users WHERE email LIKE :p"), {"p": f"%-{ws_id}@halo-tests.example.com"})
    with tenant_session(ws_id) as db:
        db.execute(text("DELETE FROM workspaces WHERE id = :w"), {"w": ws_id})


def test_new_project_defaults_to_us_dollars_and_miles(ws):
    _, c, h = ws
    r = c.post("/api/v1/properties", json=HOTEL, headers=h["manager"])
    assert r.status_code == 201, r.text
    p = r.json()
    assert (p["country"], p["currency"], p["distance_unit"]) == ("US", "USD", "mi")
    assert p["latest_job"] is None and "started_job_id" not in p
    ov = c.get(f"/api/v1/properties/{p['id']}/overview", headers=h["manager"]).json()
    assert ov["opportunities"]["currency"] == "USD"


def test_india_project_uses_rupees_and_km(ws):
    _, c, h = ws
    p = c.post("/api/v1/properties", json={**HOTEL, "country": "in"}, headers=h["manager"]).json()
    assert (p["country"], p["currency"], p["distance_unit"]) == ("IN", "INR", "km")


def test_unsupported_country_is_rejected(ws):
    _, c, h = ws
    assert c.post("/api/v1/properties", json={**HOTEL, "country": "FR"}, headers=h["manager"]).status_code == 422
    pid = c.post("/api/v1/properties", json=HOTEL, headers=h["manager"]).json()["id"]
    assert c.patch(f"/api/v1/properties/{pid}", json={"country": "FR"}, headers=h["manager"]).status_code == 422


def test_start_agent_creates_capped_first_run(ws):
    _, c, h = ws
    p = c.post("/api/v1/properties", json={**HOTEL, "start_agent": True,
                                           "target": {"radius_km": 8.047, "industries": ["it_services"]}},
               headers=h["manager"]).json()
    job = c.get(f"/api/v1/discovery/jobs/{p['started_job_id']}", headers=h["manager"]).json()
    assert job["status"] in ("queued", "running")
    assert job["config"]["max_companies"] == 50 and job["budget_usd"] == 2.0
    assert job["config"]["radius_km"] == pytest.approx(8.047) and job["config"]["industries"] == ["it_services"]
    listed = c.get("/api/v1/properties", headers=h["manager"]).json()
    assert listed[0]["latest_job"]["id"] == p["started_job_id"]


def test_delete_project_hides_it_and_stops_the_agent(ws):
    _, c, h = ws
    p = c.post("/api/v1/properties", json={**HOTEL, "start_agent": True}, headers=h["manager"]).json()
    assert c.delete(f"/api/v1/properties/{p['id']}", headers=h["rep"]).status_code == 403
    assert c.delete(f"/api/v1/properties/{p['id']}", headers=h["manager"]).status_code == 204
    assert c.get(f"/api/v1/properties/{p['id']}", headers=h["manager"]).status_code == 404
    assert c.get("/api/v1/properties", headers=h["manager"]).json() == []
    assert c.get("/api/v1/discovery/jobs", headers=h["manager"]).json() == []
    with tenant_session(ws[0]) as db:
        status = db.execute(text("SELECT status FROM discovery_jobs WHERE id = :j"), {"j": p["started_job_id"]}).scalar_one()
    assert status == "cancelled"


def test_projects_are_invisible_across_workspaces(ws):
    _, c, h = ws
    pid = c.post("/api/v1/properties", json=HOTEL, headers=h["manager"]).json()["id"]
    other = uuid7()
    with tenant_session(other) as db:
        db.add(Workspace(id=other, name=f"test-{other}", slug=f"test-{other}"))
    email = _make_user(other, "manager")
    try:
        oh = _login(c, email)
        assert c.get(f"/api/v1/properties/{pid}", headers=oh).status_code == 404
        assert c.delete(f"/api/v1/properties/{pid}", headers=oh).status_code == 404
        assert c.get("/api/v1/properties", headers=oh).json() == []
    finally:
        with plain_session() as db:
            db.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})
        with tenant_session(other) as db:
            db.execute(text("DELETE FROM workspaces WHERE id = :w"), {"w": other})


def test_rep_sees_no_runs_for_unshared_projects(ws):
    _, c, h = ws
    c.post("/api/v1/properties", json={**HOTEL, "start_agent": True}, headers=h["manager"])
    assert len(c.get("/api/v1/discovery/jobs", headers=h["manager"]).json()) == 1
    assert c.get("/api/v1/discovery/jobs", headers=h["rep"]).json() == []


def test_reference_lists_both_markets(ws):
    _, c, h = ws
    ref = c.get("/api/v1/reference", headers=h["manager"]).json()
    assert ref["default_country"] == "US"
    assert {r["code"] for r in ref["regions"]} == {"US", "IN"}
