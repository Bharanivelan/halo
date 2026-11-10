# Inhabitr — Task Tracker

> Status: `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` dropped. Requirement refs point to PRD (FR/NFR/UX).
> Last updated: 2026-11-09

## Phase 0 — Documentation & ground truth

- [x] T-0.1 PROJECT_OVERVIEW.md
- [x] T-0.2 PRD.md
- [x] T-0.3 SYSTEM_ARCHITECTURE.md
- [x] T-0.4 AGENT_ARCHITECTURE.md
- [x] T-0.5 DATABASE_SCHEMA.md
- [x] T-0.6 API_DOCUMENTATION.md
- [x] T-0.7 DEVELOPMENT_ROADMAP.md
- [x] T-0.8 DECISION_LOG.md
- [x] T-0.9 TASK_TRACKER.md
- [x] T-0.10 Ground-truth dataset template (`data/eval/`)
- [x] T-0.11 Owner review of all docs (P-09 accepted; P-10 accepted with CSS Modules instead of Tailwind; DD-01…16 accepted)
- [~] T-0.12 **Owner: research & verify 30–50 OMR-area companies** (incl. ~10 negatives; fixed pin + 15 km, D-20) — in parallel with Phase 1
- [x] T-0.13 Initialise git repository, `.gitignore`, first commit of docs

## Real build (D-24) — status 2026-11-09

Backend (FastAPI · Postgres/PostGIS · Postgres queue · worker)
- [x] Infra: Docker Compose DB, app DB role, Alembic migration, **RLS on 27 tenant tables** (tested)
- [x] Auth: Argon2id, DB sessions, HttpOnly cookie, CSRF, login rate limit, audit log
- [x] Properties, offerings, target profile, geocoding (Nominatim), overview, CSV import
- [x] Workflow engine: tasks/leases/retries/idempotency/cancel/resume/retry-failed, budget guard, job events
- [x] Providers: Overpass (rotating, backoff), Nominatim, safe fetcher (SSRF, robots.txt, per-domain throttle), GDELT, Tavily (optional)
- [x] Steps: plan → discover (OSM, CSV) → resolve → classify → research agent → signals → score (+ role recommendations)
- [x] Evidence: claims with grounding validator + DB constraint; signals grounded
- [x] Scoring v1 (versioned model in DB), explainable breakdown
- [x] Accounts API (filters, sort, cursor, bulk, export CSV, map), account detail + next action
- [x] Contacts (+ do-not-contact), copilot (LLM + template fallback, claim-ref validation), opportunities, activities
- [x] Activity: jobs, usage by step/model/job, LLM call log
- [x] Tests: 20 passing (grounding, scoring, normalisation, rules, RLS isolation)
- [~] End-to-end run with an OpenAI key (needs key in `.env`)
- [x] Eval runner: `python -m app.eval --property "<name>" --csv ../data/eval/ground_truth_omr_v1.csv` (needs owner dataset to produce numbers)
- [x] Wall-clock job limit enforcement (DD-16)

Frontend (React · CSS Modules · tokens)
- [~] Full app against the real API (in progress)

## Phase 1 — Design system & clickable prototype

- [ ] T-1.1 Scaffold `frontend/` (Vite, React, TS strict, ESLint, Prettier, Vitest, Playwright)
- [~] T-1.2 Visual identity proposal (palette, type, spacing, motion; light/dark) → owner review — UX-1 · proposal v0.1 in `docs/DESIGN_SYSTEM.md` + preview artifact, awaiting review
- [ ] T-1.3 `design/tokens.css` + CSS Modules conventions + finalise `docs/DESIGN_SYSTEM.md`
- [ ] T-1.4 Primitives (Radix-based): Button … Kbd
- [ ] T-1.5 Domain components: DataTable, Inspector, EvidenceChip, ScoreBar, FreshnessTag, RunTimeline, CostMeter, StatusPill, TierBadge, DataOriginBadge, MapPanel, Funnel, KanbanBoard, ActivityTimeline, EmptyState, ErrorState, CommandPalette — UX-3…UX-8
- [ ] T-1.6 App shell: sidebar, property switcher, top bar, ⌘K — UX-2
- [ ] T-1.7 API types + client + query hooks (hand-written from API_DOCUMENTATION; replaced by generated types in Phase 2)
- [ ] T-1.8 MSW mock layer + fixtures (all `data_origin: "mock"`), including simulated discovery job progression — P-09
- [ ] T-1.9 Screens: Login / Accept invite
- [ ] T-1.10 Screens: Onboarding, Properties list, Property form (map), Property overview — J1
- [ ] T-1.11 Screens: Discovery list, New run (NL diff, estimate, budget), CSV import wizard — J2
- [ ] T-1.12 Screen: Discovery run detail (timeline, live results, failures, cost) — J2
- [ ] T-1.13 Screen: Accounts explorer (table, inspector, filters, saved views, bulk, map) — J3
- [ ] T-1.14 Screen: Account detail (evidence, signals, score, roles, contacts, activity, related properties) — J3/J4
- [ ] T-1.15 Copilot panel (generate, edit, claim hovers, copy, mark sent) — J4
- [ ] T-1.16 Contacts list + form — J4
- [ ] T-1.17 Pipeline board + opportunity drawer — J5
- [ ] T-1.18 Overview — J3/J5
- [ ] T-1.19 Activity (jobs, logs, usage/cost)
- [ ] T-1.20 Settings (workspace, members, providers, scoring model, audit)
- [ ] T-1.21 All loading/empty/error/partial states — UX-8
- [ ] T-1.22 Responsiveness + accessibility pass — NFR-10, NFR-13
- [ ] T-1.23 Playwright smoke tests J1–J5
- [ ] T-1.24 Owner walkthrough & sign-off; record API contract changes in API_DOCUMENTATION + DECISION_LOG

## Phase 2 — Backend foundations
- [ ] T-2.1 Backend scaffold, config, logging, error handling
- [ ] T-2.2 Docker Compose (db/postgis, web, worker, frontend)
- [ ] T-2.3 Alembic baseline: identity, workspaces, properties
- [ ] T-2.4 Auth: sessions, login/logout/me, CSRF, rate limit — FR-1
- [ ] T-2.5 Invites, password reset links, roles, property access — FR-1
- [ ] T-2.6 RLS policies + cross-tenant test suite — NFR-1
- [ ] T-2.7 Properties, offerings, target profile, geocoding — FR-2
- [ ] T-2.8 Audit log — FR-1.5
- [ ] T-2.9 Demo seed — FR-14
- [ ] T-2.10 CI pipeline
- [ ] T-2.11 OpenAPI → TS client; switch auth & properties from MSW to API

## Phase 3 — Workflow engine & discovery
- [ ] T-3.1 QueueBackend + Postgres implementation
- [ ] T-3.2 Workflow engine: states, leases, retries, idempotency, cancel/resume — FR-3.9, NFR-5
- [ ] T-3.3 job_events + progress endpoint — FR-3.8
- [ ] T-3.4 LLM gateway, prompt registry, pricing, cost logging
- [ ] T-3.5 Providers: OSM, Nominatim, fetcher (SSRF/robots), web search (coverage test) — FR-3.5, NFR-4
- [ ] T-3.6 Steps S0–S5 — FR-3
- [ ] T-3.7 CSV import — FR-4
- [ ] T-3.8 BudgetGuard + estimate — FR-3.3, FR-3.4, NFR-6
- [ ] T-3.9 Run screen on real data

## Phase 4 — Research, evidence & scoring
- [ ] T-4.1 Research agent S6 — FR-5
- [ ] T-4.2 Signals S7 (GDELT) — FR-6
- [ ] T-4.3 Grounding validator S8 + DB constraint — FR-5.2
- [ ] T-4.4 Scoring S9 + versioning — FR-7
- [ ] T-4.5 Role recommendations S10 — FR-9.1
- [ ] T-4.6 Accounts API (filters, sort, export, bulk, saved views, map) — FR-8
- [ ] T-4.7 Eval runner + first report — FR-13

## Phase 5 — Copilot, contacts, pipeline, overview
- [ ] T-5.1 Contacts + DNC — FR-9
- [ ] T-5.2 Copilot + validator + versions — FR-10
- [ ] T-5.3 Opportunities, activities, board — FR-11
- [ ] T-5.4 Overview & Activity pages — FR-12
- [ ] T-5.5 Settings (providers, scoring, members)
- [ ] T-5.6 Hardening & deployment
