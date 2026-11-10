"""Unit tests for the deterministic core: grounding, scoring, normalisation, rule classification."""
import random
from datetime import datetime, timedelta, timezone

from app.discovery.common import haversine_km, normalize_name
from app.discovery.steps import rule_classify
from app.evidence.grounding import check_quote, value_consistent
from app.scoring.engine import DEFAULT_MODEL, ClaimIn, ScoreInput, SignalIn, recommend_roles, score

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)
SOURCE = "About us\nHeadquartered in Bengaluru, our 300+ strong Chennai delivery team works from Perungudi.\nCareers"


# ── grounding ──
def test_exact_quote_passes():
    assert check_quote("our 300+ strong Chennai delivery team", SOURCE)[0] == "passed"


def test_quote_normalises_whitespace_and_smart_quotes():
    assert check_quote("Headquartered   in  Bengaluru,", SOURCE)[0] == "passed"
    assert check_quote("it’s fine", "It's fine to quote this")[0] == "passed"


def test_fabricated_quote_fails():
    status, detail = check_quote("we employ 5,000 engineers in Chennai", SOURCE)
    assert status == "failed" and detail["reason"] == "quote not found in source"


def test_short_or_missing_quote_fails():
    assert check_quote("Chennai", SOURCE)[0] == "failed"
    assert check_quote(None, SOURCE)[0] == "failed"


def test_employee_value_needs_number_in_quote():
    assert value_consistent("employee_range", "201-500", "our 300+ strong Chennai delivery team")
    assert not value_consistent("employee_range", "201-500", "a leading technology company")


def test_hq_city_must_appear_in_quote():
    assert value_consistent("hq_location", {"city": "Bengaluru"}, "Headquartered in Bengaluru")
    assert not value_consistent("hq_location", {"city": "Pune"}, "Headquartered in Bengaluru")


# ── scoring ──
def _inp(**kw):
    base = dict(industry_code="it_services", offerings=["corporate_rate"], property_city="Chennai", distance_km=4.0,
                radius_km=15, claims=[
                    ClaimIn("c1", "hq_location", {"city": "Bengaluru"}, "fact", "acme.example", NOW - timedelta(days=10)),
                    ClaimIn("c2", "client_facing_services", {"value": True}, "inference"),
                    ClaimIn("c3", "employee_range", "201-500", "fact", "acme.example", NOW - timedelta(days=10)),
                    ClaimIn("c4", "local_presence", {"address": "Perungudi"}, "fact", "osm", NOW - timedelta(days=1)),
                ],
                signals=[SignalIn("s1", "new_office_or_center", "Opens new centre", NOW - timedelta(days=30), 0.9)],
                has_contact=False, has_roles=True, now=NOW)
    base.update(kw)
    return ScoreInput(**base)


def test_score_is_deterministic_and_order_independent():
    a = score(_inp(), DEFAULT_MODEL)
    claims = _inp().claims
    random.shuffle(claims)
    b = score(_inp(claims=claims), DEFAULT_MODEL)
    assert a == b


def test_score_breakdown_sums_to_fit():
    r = score(_inp(), DEFAULT_MODEL)
    assert round(sum(f["points"] for f in r["breakdown"]["fit"]["factors"])) == r["fit"]
    assert r["tier"] in ("A", "B", "C")


def test_inference_counts_half():
    fact = score(_inp(claims=[ClaimIn("c2", "client_facing_services", {"value": True}, "fact", "x.example", NOW)]), DEFAULT_MODEL)
    inf = score(_inp(claims=[ClaimIn("c2", "client_facing_services", {"value": True}, "inference")]), DEFAULT_MODEL)
    f = lambda r: next(x for x in r["breakdown"]["fit"]["factors"] if x["key"] == "inbound_travel")["value"]
    assert f(inf) == f(fact) / 2


def test_old_and_undated_signals_add_no_intent():
    old = SignalIn("s", "new_office_or_center", "x", NOW - timedelta(days=500), 1.0)
    undated = SignalIn("u", "hiring_drive", "y", None, 1.0)
    assert score(_inp(signals=[old, undated]), DEFAULT_MODEL)["intent"] == 0


def test_signal_decays_with_age():
    fresh = score(_inp(signals=[SignalIn("s", "hiring_drive", "x", NOW - timedelta(days=5), 1.0)]), DEFAULT_MODEL)["intent"]
    stale = score(_inp(signals=[SignalIn("s", "hiring_drive", "x", NOW - timedelta(days=200), 1.0)]), DEFAULT_MODEL)["intent"]
    assert fresh > stale


def test_unknowns_lower_confidence_not_fit_imputation():
    r = score(_inp(claims=[]), DEFAULT_MODEL)
    scale = next(x for x in r["breakdown"]["fit"]["factors"] if x["key"] == "scale")
    assert scale["value"] == 0 and "employee_range" in r["breakdown"]["missing"]


def test_proximity_curve():
    near = score(_inp(distance_km=1), DEFAULT_MODEL)
    far = score(_inp(distance_km=30), DEFAULT_MODEL)
    prox = lambda r: next(x for x in r["breakdown"]["fit"]["factors"] if x["key"] == "proximity")["value"]
    assert prox(near) == 1.0 and prox(far) == 0.0


def test_roles_depend_on_size():
    small = [r["role_code"] for r in recommend_roles("11-50", ["corporate_rate"], "it_services")]
    large = [r["role_code"] for r in recommend_roles("1001-5000", ["corporate_rate"], "it_services")]
    assert small[0] == "founder_ceo" and "travel_desk" in large


# ── discovery helpers ──
def test_normalize_name_strips_legal_suffixes():
    assert normalize_name("Acme Technologies Pvt. Ltd.") == normalize_name("ACME Technologies Private Limited")


def test_haversine_reasonable():
    assert 4.5 < haversine_km(12.9010, 80.2279, 12.9416, 80.2363) < 4.8


def test_rule_classify():
    assert rule_classify({"office": "it"}) == (True, "it_services")
    assert rule_classify({"office": "government"})[0] is False
    assert rule_classify({"industrial": "factory"}) == (True, "manufacturing_other")
