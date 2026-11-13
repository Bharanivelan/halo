"""Halo Lab (D-47): ratings, agent versions, improvement loop, approval and rollback.

Requires the dev database with migrations applied. No network calls (the AI is stubbed or switched off).
Stop the worker (python -m app.worker) first: improvement runs are queued as jobs.
"""
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.db import plain_session, tenant_session
from app.core.ids import uuid7
from app.core.security import hash_password
from app.main import app
from app.models import Account, Company, Membership, Signal, Source, User, WorkflowTask, Workspace

PW = "test-password-123"
HOTEL = {"name": "Lab Hotel", "location": {"lat": 40.7128, "lng": -74.0060}}


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


def _prospects(ws_id, pid, specs):
    """specs: list of (name, industry, distance_km, domain). Returns account ids in order."""
    ids = []
    with tenant_session(ws_id) as db:
        for name, ind, dist, dom in specs:
            co = Company(workspace_id=ws_id, name=name, normalized_name=name.lower(), industry_code=ind, primary_domain=dom)
            db.add(co)
            db.flush()
            a = Account(workspace_id=ws_id, property_id=UUID(pid), company_id=co.id, distance_km=dist, tier="C")
            db.add(a)
            db.flush()
            ids.append(str(a.id))
    return ids


def _project(c, h):
    return c.post("/api/v1/properties", json=HOTEL, headers=h["manager"]).json()["id"]


# ───────── B1: ratings and versions ─────────
def test_rate_a_prospect_and_see_it_everywhere(ws):
    ws_id, c, h = ws
    pid = _project(c, h)
    aid, = _prospects(ws_id, pid, [("Acme Consulting", "consulting_professional", 1.0, "acme.example")])
    r = c.put(f"/api/v1/accounts/{aid}/feedback", json={"verdict": "not_fit", "reason": "too_small"}, headers=h["manager"])
    assert r.status_code == 200 and r.json()["reason_label"] == "Too small"
    assert c.get(f"/api/v1/accounts/{aid}", headers=h["manager"]).json()["feedback"]["verdict"] == "not_fit"
    items = c.get(f"/api/v1/properties/{pid}/accounts", headers=h["manager"]).json()["items"]
    assert items[0]["feedback"] == {"verdict": "not_fit", "reason": "too_small"}
    # Re-rating replaces the old rating; a good fit carries no reason.
    r = c.put(f"/api/v1/accounts/{aid}/feedback", json={"verdict": "good_fit", "reason": "too_small"}, headers=h["manager"])
    assert r.json()["verdict"] == "good_fit" and r.json()["reason"] is None
    assert c.put(f"/api/v1/accounts/{aid}/feedback", json={"verdict": "not_fit", "reason": "bogus"},
                 headers=h["manager"]).status_code == 422
    assert c.put(f"/api/v1/accounts/{aid}/feedback", json={"verdict": "maybe"}, headers=h["manager"]).status_code == 422
    assert c.delete(f"/api/v1/accounts/{aid}/feedback", headers=h["manager"]).status_code == 204
    assert c.get(f"/api/v1/accounts/{aid}", headers=h["manager"]).json()["feedback"] is None


def test_rep_cannot_rate_prospects_of_unshared_hotels(ws):
    ws_id, c, h = ws
    pid = _project(c, h)
    aid, = _prospects(ws_id, pid, [("Acme", "consulting_professional", 1.0, None)])
    assert c.put(f"/api/v1/accounts/{aid}/feedback", json={"verdict": "good_fit"}, headers=h["rep"]).status_code == 404


def test_flag_a_signal_as_wrong(ws):
    ws_id, c, h = ws
    pid = _project(c, h)
    aid, = _prospects(ws_id, pid, [("Acme", "consulting_professional", 1.0, None)])
    with tenant_session(ws_id) as db:
        co = db.get(Account, UUID(aid)).company_id
        src = Source(workspace_id=ws_id, company_id=co, source_type="news", url="https://news.example/acme")
        db.add(src)
        db.flush()
        s = Signal(workspace_id=ws_id, company_id=co, signal_type="hiring", title="Hiring 50 people", confidence=0.8,
                   source_id=src.id)
        db.add(s)
        db.flush()
        sid = str(s.id)
    assert c.put(f"/api/v1/signals/{sid}/feedback", json={"verdict": "wrong"}, headers=h["manager"]).status_code == 200
    detail = c.get(f"/api/v1/accounts/{aid}", headers=h["manager"]).json()
    assert detail["signals"][0]["feedback"] == "wrong"
    assert c.get("/api/v1/lab/summary", headers=h["manager"]).json()["ratings"]["signals_wrong"] == 1


def test_csv_ratings_match_by_website_then_name(ws):
    ws_id, c, h = ws
    pid = _project(c, h)
    _prospects(ws_id, pid, [("Acme Consulting", "consulting_professional", 1.0, "acme.example"), ("Beta Labs", "it_services", 2.0, None)])
    csv_text = ("Company,Website,Verdict,Reason\n"
                "Acme Consulting Inc,https://www.acme.example/about,good,\n"
                "beta labs,,no,too_far\n"
                "Gamma Corp,,yes,\n"
                "Delta,,perhaps,\n")
    r = c.post(f"/api/v1/lab/ratings/import?property_id={pid}", files={"file": ("r.csv", csv_text, "text/csv")},
               headers=h["manager"])
    assert r.status_code == 200, r.text
    out = r.json()
    assert (out["created"], out["updated"], out["unmatched"]) == (2, 0, ["Gamma Corp"])
    assert out["invalid"][0]["company"] == "Delta"
    assert c.post(f"/api/v1/lab/ratings/import?property_id={pid}", files={"file": ("r.csv", csv_text, "text/csv")},
                  headers=h["rep"]).status_code == 403


def test_summary_counts_ratings_and_creates_version_one(ws):
    ws_id, c, h = ws
    pid = _project(c, h)
    ids = _prospects(ws_id, pid, [(f"Co {i}", "consulting_professional", 1.0, None) for i in range(5)])
    for aid in ids[:2]:
        c.put(f"/api/v1/accounts/{aid}/feedback", json={"verdict": "good_fit"}, headers=h["manager"])
    c.put(f"/api/v1/accounts/{ids[2]}/feedback", json={"verdict": "not_fit"}, headers=h["manager"])
    c.patch(f"/api/v1/accounts/{ids[3]}", json={"status": "dismissed", "dismissed_reason": "too_far"}, headers=h["manager"])
    c.patch(f"/api/v1/accounts/{ids[4]}", json={"status": "dismissed", "dismissed_reason": "duplicate"}, headers=h["manager"])
    s = c.get("/api/v1/lab/summary", headers=h["manager"]).json()
    assert s["ratings"]["good_fit"] == 2 and s["ratings"]["not_fit"] == 2 and s["ratings"]["from_dismissals"] == 1
    assert s["ready"] is False and "at least 12" in s["not_ready_reason"]
    assert s["active_version"]["version"] == 1 and s["active_version"]["status"] == "active"
    assert [v["version"] for v in c.get("/api/v1/lab/versions", headers=h["manager"]).json()] == [1]


def test_lab_guidance_is_added_below_the_locked_rules():
    from app.llm import prompts

    pid, ver, system = prompts.classify_prompt("Treat hospitals as low relevance.", 4)
    base = prompts.CLASSIFY[2]
    assert ver == "v1+a4" and system.startswith(base) and system.endswith("Treat hospitals as low relevance.")
    assert prompts.classify_prompt("", 4) == prompts.CLASSIFY


def test_industry_preference_changes_the_score():
    from app.scoring.engine import DEFAULT_MODEL, ScoreInput, score

    inp = ScoreInput(industry_code="consulting_professional", offerings=["corporate_rate"], property_city="Austin", distance_km=1.0,
                     radius_km=8, claims=[], signals=[], has_contact=False, has_roles=False)
    base = score(inp, DEFAULT_MODEL)["fit"]
    import copy
    m = copy.deepcopy(DEFAULT_MODEL)
    m["params"]["industry_adjust"] = {"consulting_professional": -0.5}
    assert score(inp, m)["fit"] < base


def test_edits_are_clamped_and_unknown_settings_ignored():
    from app.lab.harness import apply_edits, default_harness

    h, changes = apply_edits(default_harness(), [
        {"path": "params.tiers.A", "to": 500}, {"path": "params.tiers.B", "to": 89},
        {"path": "weights.priority.fit", "to": 0.7}, {"path": "params.evidence_rules", "to": 0},
        {"path": "params.industry_adjust.healthcare_hospital", "to": -0.3}], guidance="  Hospitals are rarely a fit.  ")
    t = h["scoring"]["params"]["tiers"]
    assert t["A"] == 90 and t["B"] == 80
    assert h["scoring"]["weights"]["priority"] == {"fit": 0.7, "intent": 0.3}
    assert h["scoring"]["params"]["industry_adjust"] == {"healthcare_hospital": -0.3}
    assert h["classify_guidance"] == "Hospitals are rarely a fit."
    assert "evidence_rules" not in str(h) and any("Score needed for Hot" in x for x in changes)
