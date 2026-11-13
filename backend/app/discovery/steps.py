"""Discovery pipeline steps (AGENT_ARCHITECTURE §2–§10).

plan → discover_osm / discover_csv → resolve → classify → per company: research → signals → score
Deterministic code everywhere except: classify (LLM batch), research (bounded agent), signals (LLM extract).
Every LLM-backed step has a rules-based fallback so the pipeline still works without an API key.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from uuid import UUID

from geoalchemy2.shape import to_shape
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.regions import region
from app.core.vocab import CLAIM_FIELDS, EMPLOYEE_RANGES, INDUSTRIES, OFFERING_LABELS, SIGNAL_TYPES
from app.discovery.common import (add_claim, haversine_km, normalize_name, osm_tags_text, parse_date, point_wkt,
                                  save_source, supersede_auto_claims)
from app.llm import gateway as llm
from app.llm import prompts
from app.models import (Account, AccountScore, Claim, Company, CompanyIdentifier, CompanyLocation, Contact, CsvImport,
                        DiscoveryResult, Property, PropertyOffering, PropertyTargetProfile, ScoringModel, Signal, Source,
                        TargetRoleRecommendation, WorkflowTask)
from app.providers import fetcher, gdelt, geocoder, osm, search
from app.providers.http import record_provider_call
from app.scoring.engine import ClaimIn, ScoreInput, SignalIn, recommend_roles, score
from app.workflow.engine import NewTask, Step, StepContext, all_terminal, lock_job, step
from app.workflow.errors import AIQuotaExhausted, PermanentError, TransientError


# ───────── helpers ─────────
def _llm_ctx(ctx: StepContext) -> llm.CallContext:
    return llm.CallContext(workspace_id=ctx.workspace_id, step=ctx.task.step, job_id=ctx.job.id, task_id=ctx.task.id,
                           budget=ctx.budget, on_cost=ctx.add_cost)


def _property(ctx: StepContext) -> tuple[Property, float, float]:
    prop = ctx.db.get(Property, ctx.job.property_id)
    pt = to_shape(prop.location)
    return prop, pt.y, pt.x


def _offerings(db: Session, property_id: UUID) -> list[str]:
    rows = db.execute(select(PropertyOffering.offering).where(PropertyOffering.property_id == property_id)).scalars().all()
    return list(rows) or ["corporate_rate"]


def _barrier_to_resolve(ctx: StepContext) -> list[NewTask]:
    lock_job(ctx.db, ctx.job.id)  # serialise concurrent discover tasks finishing at once
    for s in ("discover_osm", "discover_csv"):
        if not all_terminal(ctx.db, ctx.job.id, s, exclude=ctx.task.id):
            return []
    return [NewTask("resolve")]


# ───────── plan ─────────
@step
class PlanStep(Step):
    name, stage = "plan", "plan"

    def run(self, ctx, inp):
        cfg = ctx.job.config
        prop, lat, lng = _property(ctx)
        providers = []
        if "osm" in cfg.get("sources", []):
            providers.append("discover_osm")
        if cfg.get("csv_import_id"):
            providers.append("discover_csv")
        if not providers:
            raise PermanentError("No discovery sources selected")
        r = region(prop.country)
        dist = (f"{cfg['radius_km'] / 1.609344:.1f} miles" if r["distance_unit"] == "mi" else f"{cfg['radius_km']:g} km")
        n_ind = len(cfg.get("industries") or [])
        ctx.event(f"Searching {dist} around {prop.name} for "
                  + (f"{n_ind} {'industry' if n_ind == 1 else 'industries'}." if n_ind else "businesses in every industry."))
        if ctx.settings.llm_configured and not llm.ai_available():
            ctx.event("The AI's daily allowance is used up. This run will use map data, websites and keyword rules "
                      "instead of AI.", level="warning")
        if not ctx.settings.llm_configured:
            ctx.event(f"AI is not configured (no {ctx.settings.llm_key_name}). Classification and research will use OpenStreetMap "
                      "data and rules only.", level="warning")
        return {"providers": providers, "center": [lat, lng]}

    def next(self, ctx, output):
        return [NewTask(p) for p in output["providers"]]


# ───────── discover ─────────
@step
class DiscoverOsmStep(Step):
    name, stage, max_attempts = "discover_osm", "discover", 4

    def run(self, ctx, inp):
        cfg = ctx.job.config
        _, lat, lng = _property(ctx)
        import time
        t0 = time.monotonic()
        cands, ep = osm.query(lat, lng, float(cfg["radius_km"]), cfg.get("industries") or [])
        record_provider_call(ctx.workspace_id, ctx.job.id, ctx.task.id, "osm", "overpass_query",
                             latency_ms=int((time.monotonic() - t0) * 1000), units=1)
        for c in cands:
            ctx.db.add(DiscoveryResult(workspace_id=ctx.workspace_id, job_id=ctx.job.id, provider="osm", name=c["name"], raw=c))
        ctx.event(f"OpenStreetMap: {len(cands)} named places found.")
        return {"found": len(cands), "endpoint": ep}

    def next(self, ctx, output):
        return _barrier_to_resolve(ctx)

    def next_on_failure(self, ctx, error):
        return _barrier_to_resolve(ctx)


@step
class DiscoverCsvStep(Step):
    name, stage = "discover_csv", "discover"

    def run(self, ctx, inp):
        imp = ctx.db.get(CsvImport, UUID(ctx.job.config["csv_import_id"]))
        if imp is None:
            raise PermanentError("CSV import not found")
        n = 0
        for row in imp.rows:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            cand = {"name": name, "website": row.get("website") or None, "address": row.get("address") or None,
                    "city": row.get("city") or None, "locality": None, "lat": None, "lng": None, "tags": {},
                    "notes": row.get("notes")}
            try:
                if row.get("lat") and row.get("lng"):
                    cand["lat"], cand["lng"] = float(row["lat"]), float(row["lng"])
                elif cand["address"]:
                    hits = geocoder.geocode(", ".join(x for x in (cand["address"], cand["city"]) if x), 1)
                    if hits:
                        cand["lat"], cand["lng"], cand["locality"] = hits[0]["lat"], hits[0]["lng"], hits[0]["locality"]
            except (ValueError, TransientError, PermanentError):
                pass
            ctx.db.add(DiscoveryResult(workspace_id=ctx.workspace_id, job_id=ctx.job.id, provider="csv", name=name, raw=cand))
            n += 1
        ctx.event(f"CSV import: {n} companies loaded from {imp.file_name}.")
        return {"found": n}

    def next(self, ctx, output):
        return _barrier_to_resolve(ctx)

    def next_on_failure(self, ctx, error):
        return _barrier_to_resolve(ctx)


# ───────── resolve (dedup) ─────────
@step
class ResolveStep(Step):
    name, stage = "resolve", "resolve"

    def run(self, ctx, inp):
        db, cfg = ctx.db, ctx.job.config
        prop, plat, plng = _property(ctx)
        radius = float(cfg["radius_km"])
        results = db.execute(select(DiscoveryResult).where(DiscoveryResult.job_id == ctx.job.id,
                                                           DiscoveryResult.company_id.is_(None),
                                                           DiscoveryResult.outcome == "new")).scalars().all()
        new = merged = filtered = 0
        for r in results:
            c = r.raw
            lat, lng = c.get("lat"), c.get("lng")
            dist = haversine_km(plat, plng, lat, lng) if lat is not None and lng is not None else None
            if dist is not None and dist > radius:
                r.outcome, r.filter_reason = "filtered_out", "out_of_radius"
                filtered += 1
                continue
            domain = fetcher.registrable_domain(c["website"]) if c.get("website") else None
            company = self._match(db, ctx.workspace_id, c, domain, lat, lng)
            if company is None:
                website = fetcher.normalize_url(c["website"]) if c.get("website") else None
                company = Company(workspace_id=ctx.workspace_id, name=c["name"][:300], normalized_name=normalize_name(c["name"]),
                                  primary_domain=domain, website=website,
                                  data_origin="manual" if r.provider == "csv" else "real")
                db.add(company)
                db.flush()
                src = None
                if r.provider == "osm":
                    src = save_source(db, workspace_id=ctx.workspace_id, company_id=company.id,
                                      url=f"https://www.openstreetmap.org/{c['osm_id']}", source_type="osm",
                                      title=f"{c['name']} on OpenStreetMap", text=osm_tags_text(c["name"], c.get("tags", {})),
                                      provider="osm", license_tag="odbl", job_id=ctx.job.id)
                    db.add(CompanyIdentifier(workspace_id=ctx.workspace_id, company_id=company.id, kind="osm_id", value=c["osm_id"]))
                elif r.provider == "csv":
                    src = save_source(db, workspace_id=ctx.workspace_id, company_id=company.id, url=None,
                                      source_type="csv_import", title="CSV import",
                                      text="\n".join(f"{k}={v}" for k, v in c.items() if v and k not in ("tags",)),
                                      provider="csv", license_tag="user_provided", job_id=ctx.job.id)
                if domain:
                    db.add(CompanyIdentifier(workspace_id=ctx.workspace_id, company_id=company.id, kind="domain", value=domain))
                if lat is not None:
                    db.add(CompanyLocation(workspace_id=ctx.workspace_id, company_id=company.id, label=c["name"],
                                           address=c.get("address"), locality=c.get("locality"), city=c.get("city"),
                                           location=point_wkt(lat, lng), source_id=src.id if src else None))
                r.raw = {**c, "source_id": str(src.id) if src else None}
                r.outcome = "new"
                new += 1
            else:
                r.outcome = "merged"
                merged += 1
            r.company_id = company.id
            acc = db.execute(select(Account).where(Account.property_id == prop.id, Account.company_id == company.id)).scalar_one_or_none()
            if acc is None:
                acc = Account(workspace_id=ctx.workspace_id, property_id=prop.id, company_id=company.id,
                              distance_km=round(dist, 2) if dist is not None else None, first_seen_job_id=ctx.job.id)
                db.add(acc)
                db.flush()
            elif dist is not None and acc.distance_km is None:
                acc.distance_km = round(dist, 2)
            r.account_id = acc.id
            db.flush()
        ctx.event(f"{new} new companies, {merged} merged as duplicates, {filtered} outside the radius.")
        return {"new": new, "merged": merged, "filtered": filtered}

    @staticmethod
    def _match(db, ws, c, domain, lat, lng) -> Company | None:
        if domain:
            hit = db.execute(select(Company).join(CompanyIdentifier, CompanyIdentifier.company_id == Company.id)
                             .where(CompanyIdentifier.kind == "domain", CompanyIdentifier.value == domain)).scalars().first()
            if hit:
                return hit
        if c.get("osm_id"):
            hit = db.execute(select(Company).join(CompanyIdentifier, CompanyIdentifier.company_id == Company.id)
                             .where(CompanyIdentifier.kind == "osm_id", CompanyIdentifier.value == c["osm_id"])).scalars().first()
            if hit:
                return hit
        norm = normalize_name(c["name"])
        for comp in db.execute(select(Company).where(Company.normalized_name == norm)).scalars().all():
            locs = db.execute(select(CompanyLocation).where(CompanyLocation.company_id == comp.id)).scalars().all()
            if lat is None or not locs:
                return comp
            for loc in locs:
                if loc.location is not None:
                    p = to_shape(loc.location)
                    if haversine_km(lat, lng, p.y, p.x) <= 1.0:
                        return comp
        return None

    def next(self, ctx, output):
        return [NewTask("classify")]


# ───────── classify ─────────
OSM_RULES = [
    (("office", "it"), "it_services"), (("office", "telecommunication"), "it_services"),
    (("office", "company"), "other"), (("office", "consulting"), "consulting_professional"),
    (("office", "accountant"), "consulting_professional"), (("office", "lawyer"), "consulting_professional"),
    (("office", "financial"), "bfsi_operations"), (("office", "insurance"), "bfsi_operations"),
    (("office", "financial_advisor"), "bfsi_operations"), (("office", "estate_agent"), "real_estate_coworking"),
    (("office", "coworking"), "real_estate_coworking"), (("office", "travel_agent"), "travel_management"),
    (("office", "logistics"), "logistics"), (("office", "engineer"), "engineering_rnd"),
    (("office", "research"), "engineering_rnd"), (("office", "educational_institution"), "education"),
    (("office", "employment_agency"), "consulting_professional"), (("office", "advertising_agency"), "events_agency"),
    (("amenity", "college"), "education"), (("amenity", "university"), "education"),
    (("amenity", "hospital"), "healthcare_hospital"), (("healthcare", "hospital"), "healthcare_hospital"),
]
NOT_BUSINESS = {("office", "government"), ("office", "political_party"), ("office", "religion"),
                ("office", "association"), ("office", "ngo"), ("office", "diplomatic"), ("office", "notary"),
                ("office", "post_office"), ("office", "quango")}


def rule_classify(tags: dict) -> tuple[bool, str]:
    for k, v in NOT_BUSINESS:
        if tags.get(k) == v:
            return False, "other"
    for (k, v), code in OSM_RULES:
        if tags.get(k) == v:
            return True, code
    if tags.get("industrial") or tags.get("man_made") == "works" or tags.get("building") == "industrial":
        return True, "manufacturing_other"
    if tags.get("office"):
        return True, "other"
    return True, "other"


@step
class ClassifyStep(Step):
    name, stage = "classify", "classify"

    def run(self, ctx, inp):
        db, cfg = ctx.db, ctx.job.config
        targets = set(cfg.get("industries") or [])
        rows = db.execute(select(DiscoveryResult).where(DiscoveryResult.job_id == ctx.job.id,
                                                        DiscoveryResult.account_id.is_not(None))).scalars().all()
        by_company: dict[UUID, DiscoveryResult] = {}
        for r in rows:
            by_company.setdefault(r.company_id, r)
        companies = {c.id: c for c in db.execute(select(Company).where(Company.id.in_(list(by_company)))).scalars()}
        decisions: dict[UUID, dict] = {}

        ai_skipped = 0
        if llm.ai_available() and by_company:
            items = list(by_company.items())
            for i in range(0, len(items), 25):
                batch = items[i:i + 25]
                payload = [{"id": str(cid), "name": r.name, "tags": {k: v for k, v in (r.raw.get("tags") or {}).items()
                                                                     if not k.startswith(("addr:", "contact:phone", "phone"))},
                            "website": r.raw.get("website"), "notes": r.raw.get("notes")} for cid, r in batch]
                pid, ver, system = prompts.CLASSIFY
                user = (f"Hotel target industries: {sorted(targets) or 'any'}.\nCandidates:\n"
                        + json.dumps(payload, ensure_ascii=False))
                # D-44: one busy batch must not sink the run. Wait and retry once; then fall back to map tags
                # for this batch (handled below) and keep going. Budget and key errors still stop the step.
                out = None
                for attempt in range(2):
                    try:
                        out = llm.call_json(ctx=_llm_ctx(ctx), prompt_id=pid, version=ver, system=system, user=user,
                                            tier="fast")
                        break
                    except TransientError as e:
                        if attempt == 0:
                            time.sleep(min(60.0, e.retry_after_s or 20))
                    except AIQuotaExhausted:
                        break
                if out is None:
                    ai_skipped += len(batch)
                    continue
                for res in out.get("results", []):
                    try:
                        decisions[UUID(res["id"])] = res
                    except (KeyError, ValueError):
                        continue
        for cid, r in by_company.items():
            if cid not in decisions:
                ok, code = rule_classify(r.raw.get("tags") or {})
                rel = "high" if code in targets else ("low" if ok else "none")
                if r.provider == "csv":
                    ok, rel = True, "high"  # the user asked for these explicitly
                decisions[cid] = {"is_business_office": ok, "industry_code": code, "relevance": rel,
                                  "reason": "OpenStreetMap tags" if r.provider == "osm" else "Imported by user", "_rules": True}

        if ai_skipped:
            ctx.event(f"The AI was unavailable (rate limit), so {ai_skipped} businesses were sorted using their map tags.",
                      level="warning")
        keep, drop = [], []
        for cid, d in decisions.items():
            comp, r = companies.get(cid), by_company.get(cid)
            if comp is None or r is None:
                continue
            code = d.get("industry_code") if d.get("industry_code") in INDUSTRIES else "other"
            if not comp.industry_code:
                comp.industry_code = code
            rel = d.get("relevance", "low")
            reason = None
            if not d.get("is_business_office", True):
                reason = "not_business_office"
            elif rel == "none":
                reason = "industry_mismatch"
            elif targets and code not in targets and rel != "high" and r.provider != "csv":
                reason = "industry_mismatch"
            if reason:
                drop.append((cid, reason))
            else:
                acc = db.get(Account, r.account_id)
                pre = (1.0 if code in targets else 0.4) + {"high": 1.0, "medium": 0.6, "low": 0.2}.get(rel, 0) \
                    + (0.4 if comp.website else 0) - (acc.distance_km or 10) / 50
                keep.append((pre, cid, r.account_id, comp.name))
                if not d.get("_rules"):
                    src_id = (r.raw or {}).get("source_id")
                    src = db.get(Source, UUID(src_id)) if src_id else None
                    add_claim(db, workspace_id=ctx.workspace_id, company_id=cid, field="industry", value=code,
                              kind="inference", rationale=d.get("reason"), supports=[src.id] if src else [],
                              confidence=0.6, task_id=ctx.task.id)

        for cid, reason in drop:
            for r in rows:
                if r.company_id == cid:
                    r.outcome, r.filter_reason = "filtered_out", reason
                    acc = db.get(Account, r.account_id) if r.account_id else None
                    if acc and acc.first_seen_job_id == ctx.job.id and acc.status == "discovered":
                        db.delete(acc)
                    r.account_id = None
        keep.sort(key=lambda x: -x[0])
        limit = int(cfg.get("max_companies") or 50)
        research = [(cid, aid, name) for _, cid, aid, name in keep[:limit]]
        score_only = [(cid, aid, name) for _, cid, aid, name in keep[limit:]]
        ctx.event(f"Kept {len(keep)} relevant companies ({len(drop)} filtered out). Researching the top {len(research)}"
                  + (f"; {len(score_only)} more scored from basic data." if score_only else "."))
        return {"research": [[str(a), str(b), n] for a, b, n in research],
                "score_only": [[str(a), str(b), n] for a, b, n in score_only], "dropped": len(drop)}

    def next(self, ctx, output):
        tasks = [NewTask("research", subject_id=UUID(c), subject_label=n, input={"company_id": c, "account_id": a}, priority=1)
                 for c, a, n in output["research"]]
        tasks += [NewTask("score", subject_id=UUID(c), subject_label=n, input={"company_id": c, "account_id": a})
                  for c, a, n in output["score_only"]]
        return tasks


# ───────── research (bounded agent) ─────────
TOOLS_FETCH = {"type": "function", "function": {
    "name": "fetch_page", "description": "Fetch a web page and return its text. Use URLs from the candidate list, links on fetched pages of the same site, or search results.",
    "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}}
TOOLS_SEARCH = {"type": "function", "function": {
    "name": "web_search", "description": "Search the web. Returns titles, URLs and snippets.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}
TOOLS_FINISH = {"type": "function", "function": {
    "name": "finish", "description": "Submit the evidence-backed company profile. Call exactly once.",
    "parameters": {"type": "object", "properties": {
        "claims": {"type": "array", "items": {"type": "object", "properties": {
            "field": {"type": "string", "enum": list(CLAIM_FIELDS)},
            "value": {"description": "Value in the documented format for this field"},
            "kind": {"type": "string", "enum": ["fact", "inference", "unknown"]},
            "source_id": {"type": ["string", "null"], "description": "e.g. S1"},
            "evidence_quote": {"type": ["string", "null"]},
            "rationale": {"type": ["string", "null"]},
            "supports": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"}}, "required": ["field", "kind"]}},
        "unknowns": {"type": "array", "items": {"type": "string"}}}, "required": ["claims"]}}}


def _wrap(sid: str, url: str, title: str | None, text: str, limit: int) -> str:
    return f'<untrusted_source id="{sid}" url="{url}" title="{(title or "")[:120]}">\n{text[:limit]}\n</untrusted_source>'


def _page_text(page: fetcher.FetchedPage) -> str:
    head = "\n".join(x for x in (page.title, page.description) if x)
    return (head + "\n" + page.text).strip()


@step
class ResearchStep(Step):
    name, stage, max_attempts = "research", "research", 2

    def run(self, ctx, inp):
        db, s = ctx.db, ctx.settings
        company = db.get(Company, UUID(inp["company_id"]))
        prop = db.get(Property, ctx.job.property_id)
        supersede_auto_claims(db, company.id)
        stats = {"pages": 0, "facts": 0, "inferences": 0, "unknown": 0, "downgraded": 0, "searches": 0}

        # 1) Facts straight from OpenStreetMap / CSV source records.
        base_src = db.execute(select(Source).where(Source.company_id == company.id,
                                                   Source.source_type.in_(("osm", "csv_import")))
                              .order_by(Source.retrieved_at.desc()).limit(1)).scalar_one_or_none()
        if base_src and base_src.content_text:
            txt = base_src.content_text
            m = re.search(r"^(?:website|contact:website|url)=(.+)$", txt, re.M)
            if m and not company.website:
                company.website = fetcher.normalize_url(m.group(1).strip())
                company.primary_domain = fetcher.registrable_domain(company.website)
            addr_lines = [ln for ln in txt.splitlines() if ln.startswith(("addr:street=", "addr:suburb=", "address="))]
            if addr_lines:
                loc = db.execute(select(CompanyLocation).where(CompanyLocation.company_id == company.id)).scalars().first()
                add_claim(db, workspace_id=ctx.workspace_id, company_id=company.id, field="local_presence",
                          value={"address": (loc.address if loc and loc.address else addr_lines[0].split("=", 1)[1]), "type": "unknown"},
                          kind="fact", source=base_src, quote=addr_lines[0], confidence=0.8, task_id=ctx.task.id)

        # 2) Find the website if we don't have one (needs web search).
        search_urls: set[str] = set()
        if not company.website and search.available():
            res = search.search(f"{company.name} {prop.city or ''} official website", 5)
            stats["searches"] += 1
            record_provider_call(ctx.workspace_id, ctx.job.id, ctx.task.id, "tavily", "search", s.tavily_cost_per_search_usd)
            ctx.add_cost(s.tavily_cost_per_search_usd)
            tokens = [t for t in normalize_name(company.name).split() if len(t) > 2]
            for it in res:
                dom = fetcher.registrable_domain(it["url"] or "")
                if not dom or dom in search.NOT_COMPANY_SITES:
                    continue
                if any(t in dom.replace("-", "") for t in tokens) or any(t in (it["title"] or "").lower() for t in tokens[:1]):
                    company.website, company.primary_domain = fetcher.normalize_url(f"https://{dom}"), dom
                    break
        if company.primary_domain and not db.execute(select(CompanyIdentifier).where(
                CompanyIdentifier.kind == "domain", CompanyIdentifier.value == company.primary_domain)).first():
            db.add(CompanyIdentifier(workspace_id=ctx.workspace_id, company_id=company.id, kind="domain", value=company.primary_domain))

        if not company.website:
            company.research_status, company.research_note = "researched", "No website found; profile based on map data only."
            company.last_researched_at = datetime.now(timezone.utc)
            ctx.event(f"{company.name}: no website listed, so we used map data.")
            return stats

        # 3) Homepage.
        try:
            home = fetcher.fetch(company.website)
        except (PermanentError, TransientError) as e:
            # A slow or down website gets one retry; after that, continue on map data (D-45) instead of failing the step.
            if isinstance(e, TransientError) and ctx.task.attempt < ctx.task.max_attempts:
                raise
            company.research_status, company.research_note = "researched", f"Website unavailable: {e}"
            company.last_researched_at = datetime.now(timezone.utc)
            # Plain wording for the live log (D-45); the technical reason stays in research_note.
            ctx.event(f"{company.name}: couldn't read their website (some sites block automated visits), "
                      "so we used map data.")
            return stats
        sources: dict[str, Source] = {}
        texts: dict[str, str] = {}
        home_src = save_source(db, workspace_id=ctx.workspace_id, company_id=company.id, url=home.final_url,
                               source_type="website", title=home.title, text=_page_text(home),
                               published_at=home.published_at, job_id=ctx.job.id, http_status=home.status)
        sources["S1"], texts["S1"] = home_src, _page_text(home)
        stats["pages"] = 1
        site = fetcher.registrable_domain(home.final_url)
        if site and site != company.primary_domain:
            company.primary_domain = site
        company.website = home.final_url

        if not llm.ai_available():
            if home.description:
                add_claim(db, workspace_id=ctx.workspace_id, company_id=company.id, field="description",
                          value=home.description[:300], kind="fact", source=home_src, quote=home.description[:240],
                          confidence=0.7, task_id=ctx.task.id)
                if not company.description:
                    company.description = home.description[:300]
            add_claim(db, workspace_id=ctx.workspace_id, company_id=company.id, field="website", value=home.final_url,
                      kind="fact", source=home_src, quote=(home.title or home.text[:60])[:120], confidence=0.9, task_id=ctx.task.id)
            company.research_status, company.last_researched_at = "researched", datetime.now(timezone.utc)
            company.research_note = "AI not configured: website fetched, detailed extraction skipped."
            return stats

        # 4) Bounded agent loop.
        limits = s.research_depths.get(ctx.job.config.get("research_depth", "standard"), s.research_depths["standard"])
        allowed = set(fetcher.candidate_links(home, 20)) | {home.final_url}
        tools = [TOOLS_FETCH, TOOLS_FINISH] + ([TOOLS_SEARCH] if search.available() else [])
        seed = {"name": company.name, "known_website": company.website, "osm_or_csv_record": (base_src.content_text if base_src else None),
                "hotel_city": prop.city, "hotel_locality": prop.locality}
        lim = s.page_text_chars_for_llm
        user = (f"Company to research:\n{json.dumps(seed, ensure_ascii=False)}\n\nHomepage (source S1):\n"
                f"{_wrap('S1', home.final_url, home.title, texts['S1'], lim)}\n\nCandidate pages on this site:\n"
                + "\n".join(sorted(allowed - {home.final_url})[:20]))
        pid, ver, system = prompts.RESEARCH
        messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        calls, cost0, finish_args = 0, ctx.cost_usd, None
        for _turn in range(int(limits["max_tool_calls"]) + 3):
            force = (calls >= limits["max_tool_calls"] or stats["pages"] >= limits["max_pages"]
                     or ctx.cost_usd - cost0 >= limits["max_cost_usd"])
            res = llm.call(ctx=_llm_ctx(ctx), prompt_id=pid, version=ver, messages=messages, tier="standard",
                           tools=tools, tool_choice={"type": "function", "function": {"name": "finish"}} if force else "auto",
                           max_output_tokens=8000)
            if not res.tool_calls:
                messages.append({"role": "assistant", "content": res.content or ""})
                messages.append({"role": "user", "content": "Call finish now with your claims."})
                calls += 1
                continue
            messages.append({"role": "assistant", "content": res.content or None, "tool_calls": [
                {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                 **({"extra_content": tc["extra_content"]} if tc.get("extra_content") else {})}
                for tc in res.tool_calls]})
            for tc in res.tool_calls:
                name, args = tc["name"], tc["arguments"]
                if name == "finish":
                    finish_args = args
                    content = "ok"
                elif name == "fetch_page":
                    content = self._tool_fetch(ctx, company, args.get("url", ""), allowed, search_urls, site, sources, texts, stats, lim)
                elif name == "web_search" and search.available() and stats["searches"] < 2:
                    stats["searches"] += 1
                    record_provider_call(ctx.workspace_id, ctx.job.id, ctx.task.id, "tavily", "search", s.tavily_cost_per_search_usd)
                    ctx.add_cost(s.tavily_cost_per_search_usd)
                    hits = search.search(str(args.get("query", ""))[:200], 5)
                    for h in hits:
                        search_urls.add(h["url"])
                    content = json.dumps(hits, ensure_ascii=False)[:4000]
                else:
                    content = "Tool not available."
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": content})
                calls += 1
            if finish_args is not None:
                break

        # 5) Persist grounded claims.
        for cl in (finish_args or {}).get("claims", []):
            fld = cl.get("field")
            if fld not in CLAIM_FIELDS:
                continue
            kind = cl.get("kind") if cl.get("kind") in ("fact", "inference", "unknown") else "unknown"
            src = sources.get(str(cl.get("source_id") or "").strip())
            value = self._clean_value(fld, cl.get("value"))
            if kind != "unknown" and value is None:
                kind = "unknown"
            supports = [sources[x].id for x in (cl.get("supports") or []) if x in sources]
            claim = add_claim(db, workspace_id=ctx.workspace_id, company_id=company.id, field=fld, value=value, kind=kind,
                              source=src, quote=cl.get("evidence_quote"), rationale=cl.get("rationale"), supports=supports,
                              confidence=float(cl.get("confidence") or 0.6), task_id=ctx.task.id)
            if kind == "fact" and claim.kind == "unknown":
                stats["downgraded"] += 1
            stats[{"fact": "facts", "inference": "inferences"}.get(claim.kind, "unknown")] += 1
        db.flush()
        self._project(db, company)
        company.research_status, company.last_researched_at = "researched", datetime.now(timezone.utc)
        company.research_note = None
        if stats["downgraded"]:
            ctx.event(f"{company.name}: {stats['downgraded']} unverifiable statement(s) downgraded to Unknown.", stage="research")
        return stats

    def _tool_fetch(self, ctx, company, url, allowed, search_urls, site, sources, texts, stats, lim) -> str:
        if not url:
            return "Error: url required."
        url = fetcher.normalize_url(url)
        same_site = fetcher.registrable_domain(url) == site
        if url not in allowed and url not in search_urls and not same_site:
            return "Error: URL not allowed. Use candidate links, same-site links, or search results."
        if stats["pages"] >= ctx.settings.research_depths.get(ctx.job.config.get("research_depth", "standard"), {}).get("max_pages", 6):
            return "Error: page budget used up. Call finish."
        try:
            page = fetcher.fetch(url)
        except (PermanentError, TransientError) as e:
            return f"Error fetching page: {e}"
        sid = f"S{len(sources) + 1}"
        src = save_source(ctx.db, workspace_id=ctx.workspace_id, company_id=company.id, url=page.final_url,
                          source_type="website" if fetcher.registrable_domain(page.final_url) == site else "search_result",
                          title=page.title, text=_page_text(page), published_at=page.published_at, job_id=ctx.job.id,
                          http_status=page.status)
        sources[sid], texts[sid] = src, _page_text(page)
        stats["pages"] += 1
        if fetcher.registrable_domain(page.final_url) == site:
            for link in fetcher.candidate_links(page, 10):
                allowed.add(link)
        return _wrap(sid, page.final_url, page.title, texts[sid], lim)

    @staticmethod
    def _clean_value(field: str, v):
        if v in (None, "", [], {}):
            return None
        if field == "industry":
            return v if v in INDUSTRIES else None
        if field == "employee_range":
            v = v.get("range") if isinstance(v, dict) else v
            return v if v in EMPLOYEE_RANGES else None
        if field == "hq_location":
            if isinstance(v, str):
                return {"city": v.split(",")[0].strip(), "country": None}
            return v if isinstance(v, dict) and v.get("city") else None
        if field in ("other_locations", "business_activities", "notable_clients_or_partners", "travel_indicators"):
            if isinstance(v, str):
                v = [x.strip() for x in v.split(",") if x.strip()]
            return [str(x)[:120] for x in v][:12] if isinstance(v, list) else None
        if field in ("client_facing_services", "has_training_or_onboarding", "hosts_events"):
            if isinstance(v, bool):
                return {"value": v, "note": None}
            return v if isinstance(v, dict) else {"value": str(v).lower() in ("true", "yes"), "note": str(v)[:200]}
        if field == "description":
            return str(v)[:400]
        return v

    @staticmethod
    def _project(db: Session, company: Company) -> None:
        """Denormalise the best current claims onto the company row for fast filtering."""
        claims = db.execute(select(Claim).where(Claim.company_id == company.id, Claim.is_current.is_(True),
                                                Claim.kind != "unknown")).scalars().all()
        best: dict[str, Claim] = {}
        for c in claims:
            if c.field not in best or (c.kind == "fact" and best[c.field].kind != "fact"):
                best[c.field] = c
        if "industry" in best and best["industry"].value in INDUSTRIES:
            company.industry_code = best["industry"].value
        if "employee_range" in best and best["employee_range"].kind == "fact":
            company.employee_range = best["employee_range"].value
        if "description" in best:
            company.description = str(best["description"].value)[:500]
        if "hq_location" in best and isinstance(best["hq_location"].value, dict):
            company.hq_city = best["hq_location"].value.get("city")
            company.hq_country = best["hq_location"].value.get("country")

    def on_failure(self, ctx, error):
        comp = ctx.db.get(Company, UUID(ctx.task.input["company_id"]))
        if comp:
            comp.research_status, comp.research_note = "failed", str(error)[:300]

    def next(self, ctx, output):
        return [NewTask("signals", subject_id=ctx.task.subject_id, subject_label=ctx.task.subject_label, input=ctx.task.input)]

    def next_on_failure(self, ctx, error):
        return self.next(ctx, {})


# ───────── signals ─────────
_news_notice_jobs: set = set()
SIGNAL_KEYWORDS = [
    (re.compile(r"\b(inaugurat|opens?|opened|launch(es|ed)?) (a |its )?(new )?(office|centre|center|campus|facility|hub)", re.I), "new_office_or_center"),
    (re.compile(r"\b(expan(d|ds|sion)|new plant|capacity addition|invest(s|ment) of)", re.I), "facility_expansion"),
    (re.compile(r"\b(hiring|to hire|recruit|jobs? for|walk-?in drive|freshers)", re.I), "hiring_drive"),
    (re.compile(r"\b(conference|summit|conclave|expo|hackathon|annual meet|event)\b", re.I), "event_or_conference"),
    (re.compile(r"\b(raises?|funding|series [a-e]|acquir|merger)", re.I), "funding_or_growth"),
    (re.compile(r"\b(wins?|bags?|awarded|signs?) .{0,30}(contract|deal|order|project)", re.I), "new_project_or_client"),
]


@step
class SignalsStep(Step):
    name, stage, max_attempts = "signals", "signals", 4

    def run(self, ctx, inp):
        db, s = ctx.db, ctx.settings
        company = db.get(Company, UUID(inp["company_id"]))
        prop = db.get(Property, ctx.job.property_id)
        items: list[dict] = []
        # News from GDELT (free, strictly rate-limited). Best effort, single try: if it's busy, continue with website
        # signals and say so once per run (D-45), rather than retrying every company and flooding the activity log.
        try:
            news = gdelt.search(company.name, prop.city, region(prop.country)["label"])[:10]
        except TransientError:
            news = []
            if ctx.job.id not in _news_notice_jobs:
                _news_notice_jobs.add(ctx.job.id)
                ctx.event("The free news service is busy, so some companies were checked for signals on their own "
                          "websites only.", level="warning")
        for a in news:
            items.append({"id": f"N{len(items) + 1}", "kind": "news", "title": a["title"], "text": a["title"], "url": a["url"],
                          "published_at": a["published_at"].date().isoformat() if a["published_at"] else None})
        record_provider_call(ctx.workspace_id, ctx.job.id, ctx.task.id, "gdelt", "doc_search")
        # News-like pages fetched during research.
        pages = db.execute(select(Source).where(Source.company_id == company.id, Source.source_type == "website",
                                                Source.job_id == ctx.job.id)).scalars().all()
        for p in pages:
            if p.url and re.search(r"(news|press|media|events?|careers?|jobs|blog)", p.url, re.I):
                items.append({"id": f"N{len(items) + 1}", "kind": "page", "title": p.title or p.url, "url": p.url,
                              "text": (p.content_text or "")[:2500], "source_db_id": str(p.id),
                              "published_at": p.published_at.date().isoformat() if p.published_at else None})
        if search.available() and company.website:
            hits = search.search(f'"{company.name}" {prop.city or ""} news', 5)
            record_provider_call(ctx.workspace_id, ctx.job.id, ctx.task.id, "tavily", "search", s.tavily_cost_per_search_usd)
            ctx.add_cost(s.tavily_cost_per_search_usd)
            for h in hits:
                items.append({"id": f"N{len(items) + 1}", "kind": "search", "title": h["title"] or h["url"], "url": h["url"],
                              "text": f"{h['title']}\n{h['snippet']}", "published_at": (h.get("published_at") or "")[:10] or None})
        if not items:
            return {"signals": 0, "candidates": 0}

        found: list[dict] = []
        use_rules = not llm.ai_available()
        if not use_rules:
            pid, ver, system = prompts.SIGNALS
            user = (f"Company: {company.name}\nWebsite: {company.website}\nDescription: {company.description or 'unknown'}\n"
                    f"Hotel city: {prop.city}\nToday: {datetime.now(timezone.utc).date().isoformat()}\nItems:\n"
                    + "\n".join(_wrap(i["id"], i["url"] or "", i["title"], f"[date: {i['published_at'] or 'unknown'}]\n{i['text']}", 2500)
                                for i in items))
            try:
                out = llm.call_json(ctx=_llm_ctx(ctx), prompt_id=pid, version=ver, system=system, user=user, tier="fast")
                found = out.get("signals", []) or []
            except AIQuotaExhausted:
                use_rules = True  # daily AI allowance ran out mid-run: use keyword rules (D-44)
        if use_rules:
            for it in items:
                if it["kind"] == "page":
                    continue
                for rx, typ in SIGNAL_KEYWORDS:
                    if rx.search(it["title"]):
                        found.append({"source_id": it["id"], "signal_type": typ, "title": it["title"][:90],
                                      "description": None, "evidence_quote": it["title"], "published_at": it["published_at"],
                                      "confidence": 0.4, "implied_offerings": SIGNAL_TYPES[typ][1], "recommended_approach": None})
                        break

        by_id = {i["id"]: i for i in items}
        saved = 0
        now = datetime.now(timezone.utc)
        for sg in found:
            it = by_id.get(str(sg.get("source_id")))
            typ = sg.get("signal_type")
            if not it or typ not in SIGNAL_TYPES:
                continue
            pub = parse_date(sg.get("published_at")) or parse_date(it.get("published_at"))
            if pub and pub > now:
                pub = None
            if it.get("source_db_id"):
                src = db.get(Source, UUID(it["source_db_id"]))
            else:
                src = save_source(db, workspace_id=ctx.workspace_id, company_id=company.id, url=it["url"],
                                  source_type="news" if it["kind"] == "news" else "search_result", title=it["title"],
                                  text=it["text"], published_at=pub, provider="gdelt" if it["kind"] == "news" else "tavily",
                                  job_id=ctx.job.id)
            from app.evidence.grounding import check_quote
            g, _ = check_quote(sg.get("evidence_quote"), src.content_text)
            if g == "failed":
                continue  # an unverifiable signal is not stored
            exists = db.execute(select(Signal).where(Signal.company_id == company.id, Signal.signal_type == typ,
                                                     Signal.source_id == src.id)).scalar_one_or_none()
            if exists:
                continue
            offs = [o for o in (sg.get("implied_offerings") or SIGNAL_TYPES[typ][1]) if o in OFFERING_LABELS]
            db.add(Signal(workspace_id=ctx.workspace_id, company_id=company.id, signal_type=typ,
                          title=str(sg.get("title") or it["title"])[:200], description=sg.get("description"),
                          source_id=src.id, evidence_quote=sg.get("evidence_quote"), published_at=pub,
                          confidence=max(0.0, min(1.0, float(sg.get("confidence") or 0.5))), implied_offerings=offs,
                          recommended_approach=sg.get("recommended_approach"), grounding_status=g, produced_by_task_id=ctx.task.id))
            saved += 1
        if saved:
            ctx.event(f"{company.name}: {saved} business signal(s) found.")
        return {"signals": saved, "candidates": len(items)}

    def next(self, ctx, output):
        return [NewTask("score", subject_id=ctx.task.subject_id, subject_label=ctx.task.subject_label, input=ctx.task.input)]

    def next_on_failure(self, ctx, error):
        return self.next(ctx, {})


# ───────── score ─────────
def compute_and_store_score(db: Session, workspace_id: UUID, account: Account, task_id: UUID | None = None) -> AccountScore:
    company = db.get(Company, account.company_id)
    prop = db.get(Property, account.property_id)
    target = db.execute(select(PropertyTargetProfile).where(PropertyTargetProfile.property_id == prop.id)).scalar_one_or_none()
    model = db.execute(select(ScoringModel).where(ScoringModel.is_active.is_(True)).order_by(ScoringModel.version.desc())).scalars().first()
    if model is None:
        raise PermanentError("No active scoring model in this workspace")
    offerings = _offerings(db, prop.id)
    claims = db.execute(select(Claim, Source).outerjoin(Source, Source.id == Claim.source_id)
                        .where(Claim.company_id == company.id, Claim.is_current.is_(True))).all()
    cin = [ClaimIn(id=str(c.id), field=c.field, value=c.value, kind=c.kind,
                   source_domain=(fetcher.registrable_domain(src.url) if src and src.url else (src.source_type if src else None)),
                   source_date=(src.published_at or src.retrieved_at) if src else None) for c, src in claims]
    sigs = db.execute(select(Signal).where(Signal.company_id == company.id)).scalars().all()
    sin = [SignalIn(id=str(x.id), signal_type=x.signal_type, title=x.title, published_at=x.published_at, confidence=x.confidence) for x in sigs]
    has_contact = db.execute(select(func.count()).select_from(Contact).where(
        Contact.company_id == company.id, Contact.do_not_contact.is_(False), Contact.archived_at.is_(None),
        (Contact.email.is_not(None)) | (Contact.phone.is_not(None)))).scalar_one() > 0
    roles = recommend_roles(company.employee_range, offerings, company.industry_code)
    result = score(ScoreInput(industry_code=company.industry_code, offerings=offerings, property_city=prop.city,
                              distance_km=account.distance_km, radius_km=target.radius_km if target else 15,
                              claims=cin, signals=sin, has_contact=has_contact, has_roles=bool(roles)), {"weights": model.weights, "params": model.params})
    sc = AccountScore(workspace_id=workspace_id, account_id=account.id, scoring_model_id=model.id, model_version=model.version,
                      fit=result["fit"], intent=result["intent"], confidence=result["confidence"],
                      actionability=result["actionability"], priority=result["priority"], tier=result["tier"],
                      breakdown=result["breakdown"], computed_by_task_id=task_id)
    db.add(sc)
    db.flush()
    account.current_score_id, account.fit, account.intent, account.confidence = sc.id, sc.fit, sc.intent, sc.confidence
    account.priority, account.tier, account.actionability = sc.priority, sc.tier, sc.actionability
    db.execute(delete(TargetRoleRecommendation).where(TargetRoleRecommendation.account_id == account.id))
    for r in roles:
        db.add(TargetRoleRecommendation(workspace_id=workspace_id, account_id=account.id, **r))
    return sc


@step
class ScoreStep(Step):
    name, stage = "score", "score"

    def run(self, ctx, inp):
        acc = ctx.db.get(Account, UUID(inp["account_id"]))
        if acc is None:
            return {"skipped": "account removed"}
        sc = compute_and_store_score(ctx.db, ctx.workspace_id, acc, ctx.task.id)
        if sc.tier == "A":
            comp = ctx.db.get(Company, acc.company_id)
            ctx.event(f"Tier A: {comp.name} (priority {sc.priority:g}).", stage="score")
        return {"tier": sc.tier, "priority": sc.priority}


def task_counts_by_step(db: Session, job_id: UUID) -> dict[str, int]:
    rows = db.execute(select(WorkflowTask.step, func.count()).where(WorkflowTask.job_id == job_id).group_by(WorkflowTask.step)).all()
    return {r[0]: r[1] for r in rows}
