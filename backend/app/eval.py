"""Evaluation runner (AGENT_ARCHITECTURE §13): compare a property's accounts with the hand-verified ground truth.

Usage:
  python -m app.eval --property "<property name or id>" --csv ../data/eval/ground_truth_omr_v1.csv [--json out.json]

Matching: website domain first, then normalised name. Metrics are printed and (optionally) written as JSON.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from uuid import UUID

from sqlalchemy import select, text

from app.core.db import plain_session, tenant_session
from app.discovery.common import normalize_name
from app.models import Account, Claim, Company, Property, Signal
from app.providers.fetcher import registrable_domain


def load_truth(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("record_id") and not r["record_id"].startswith("GT-000")]
    if not rows:
        sys.exit("No ground-truth rows found (the GT-000 example row is ignored).")
    return rows


def run(property_ref: str, csv_path: str) -> dict:
    truth = load_truth(csv_path)
    # Workspace ids come from memberships (a global table); then search each workspace under RLS.
    with plain_session() as db:
        wss = [r[0] for r in db.execute(text("SELECT DISTINCT workspace_id FROM memberships"))]
    for ws in wss:
        with tenant_session(ws) as db:
            q = select(Property)
            try:
                q = q.where(Property.id == UUID(property_ref))
            except ValueError:
                q = q.where(Property.name == property_ref)
            prop = db.execute(q).scalar_one_or_none()
            if prop:
                return evaluate(db, prop, truth)
    sys.exit(f"Property '{property_ref}' not found.")


def evaluate(db, prop: Property, truth: list[dict]) -> dict:
    rows = db.execute(select(Account, Company).join(Company, Company.id == Account.company_id)
                      .where(Account.property_id == prop.id)).all()
    by_domain = {c.primary_domain: (a, c) for a, c in rows if c.primary_domain}
    by_name = {normalize_name(c.name): (a, c) for a, c in rows}

    matched, truth_relevant = [], [t for t in truth if t.get("is_relevant_target", "").upper() == "Y"]
    negatives = [t for t in truth if t.get("is_relevant_target", "").upper() == "N"]
    for t in truth:
        dom = registrable_domain(t["website_domain"]) if t.get("website_domain") else None
        hit = by_domain.get(dom) if dom else None
        hit = hit or by_name.get(normalize_name(t["company_name"]))
        matched.append((t, hit))

    found_relevant = [(t, h) for t, h in matched if h and t in truth_relevant]
    found_negative = [(t, h) for t, h in matched if h and t in negatives and h[0].status != "dismissed"]

    def fact(company_id, field):
        return db.execute(select(Claim).where(Claim.company_id == company_id, Claim.field == field,
                                              Claim.is_current.is_(True), Claim.kind == "fact")).scalars().first()

    ind_ok = ind_n = emp_ok = emp_n = sig_ok = sig_n = 0
    for t, (a, c) in found_relevant:
        if t.get("industry_code") and t["industry_code"] != "U":
            ind_n += 1
            ind_ok += int(c.industry_code == t["industry_code"])
        f = fact(c.id, "employee_range")
        if f and t.get("employee_range") and t["employee_range"] != "U":
            emp_n += 1
            emp_ok += int(f.value == t["employee_range"])
        if t.get("recent_signal_url"):
            sig_n += 1
            sig_ok += int(db.execute(select(Signal).where(Signal.company_id == c.id)).first() is not None)

    high = {t["record_id"] for t in truth if t.get("hotel_potential") == "high"}
    ranked = sorted([(h[0].priority or 0, t["record_id"]) for t, h in matched if h], reverse=True)
    top = {rid for _, rid in ranked[: max(1, len(high))]}

    pct = lambda a, b: round(100 * a / b, 1) if b else None
    metrics = {
        "property": prop.name,
        "ground_truth_rows": len(truth), "relevant_rows": len(truth_relevant), "negative_rows": len(negatives),
        "accounts_in_system": len(rows),
        "discovery_recall_pct": pct(len(found_relevant), len(truth_relevant)),
        "negatives_wrongly_kept": len(found_negative),
        "industry_accuracy_pct": pct(ind_ok, ind_n), "industry_checked": ind_n,
        "employee_range_accuracy_pct": pct(emp_ok, emp_n), "employee_range_checked": emp_n,
        "signal_found_pct": pct(sig_ok, sig_n), "signals_checked": sig_n,
        "ranking_agreement_pct": pct(len(top & high), len(high)),
        "missed": [t["company_name"] for t, h in matched if not h and t in truth_relevant][:50],
    }
    return metrics


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--property", required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--json")
    a = p.parse_args()
    m = run(a.property, a.csv)
    for k, v in m.items():
        print(f"{k:32} {v}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)


if __name__ == "__main__":
    main()
