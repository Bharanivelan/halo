# Inhabitr — Development Roadmap

> Version 1.0 · 2026-11-09 · MVP = Phases 0–5. Each phase ends with a review before the next begins.
> Rule: no phase starts backend work the docs don't describe; if reality differs, update docs + DECISION_LOG first.

---

## Phase 0 — Documentation & ground truth  *(current)*

| Deliverable | Owner | Status |
|---|---|---|
| 9 project documents | Claude | ✅ drafted, awaiting review |
| Ground-truth dataset template | Claude | ✅ |
| Ground-truth dataset (30–50 OMR-area companies, incl. ~10 negatives) | You (manual research) | ⏳ |

**Exit:** docs reviewed and accepted; dataset has ≥ 30 verified rows (can continue in parallel with Phase 1).
**Learning topics:** evaluation datasets, precision vs recall, why ground truth must be built by hand.

---

## Phase 1 — Design system & clickable prototype  *(next)*

Goal: a polished, clickable frontend covering **all five journeys (J1–J5)** on mock data served through the documented API contract (MSW), so moving to the real backend later means turning the mocks off.

| Step | Deliverable |
|---|---|
| 1.1 Visual identity | Inhabitr brand direction: palette (warm neutrals + one accent + semantic + evidence colours), typography scale, spacing, radii, elevation, motion rules, light & dark themes → `design/tokens.css` + `docs/DESIGN_SYSTEM.md` |
| 1.2 Primitives | Button, IconButton, Input, Select, Combobox, Checkbox, Radio, Switch, Tabs, Tooltip, Popover, Dialog, Sheet/Drawer, Menu, Toast, Badge, Avatar, Skeleton, Kbd |
| 1.3 Domain components | DataTable (sort, filter chips, column picker, bulk bar, virtualised), Inspector panel, **EvidenceChip** + source popover, **ScoreBar** + breakdown, **FreshnessTag**, **RunTimeline**, StageCounter, CostMeter, StatusPill, TierBadge, DataOriginBadge (Mock/Hypothetical), MapPanel (property pin, radius ring, markers), Funnel, KanbanBoard, ActivityTimeline, EmptyState, ErrorState, CommandPalette |
| 1.4 App shell | Sidebar nav (main + system), property switcher, top bar (search/⌘K, user menu), breadcrumbs, responsive collapse |
| 1.5 Screens | See screen list below |
| 1.6 Mock layer | MSW handlers per API section; typed fixtures (`data_origin: "mock"`); simulated discovery job progress over time (so the run screen actually animates through stages, with partial results and a failure) |
| 1.7 States | Loading skeletons, empty, partial, error, permission-denied for each screen |
| 1.8 Responsiveness & a11y | 1280+ primary; tablet layouts; keyboard paths; contrast checks; reduced motion |
| 1.9 Journey walkthrough | J1–J5 scripted walkthrough + Playwright smoke tests for each journey |

**Screens (mapped to journeys)**

| # | Screen | Journey |
|---|---|---|
| 1 | Login, Accept invite | — |
| 2 | Onboarding (first-run: workspace → first property) | J1 |
| 3 | Properties list · Property create/edit (multi-section form with map) · Property overview | J1 |
| 4 | Discovery runs list · New run (config, NL request diff, sources, estimate, budget) | J2 |
| 5 | Discovery run detail (timeline, live results, failures, cost) · CSV import wizard | J2 |
| 6 | Accounts explorer (table + inspector, saved views, bulk, map toggle) | J3 |
| 7 | Account detail (overview, evidence, signals, score, roles, contacts, copilot, activity, related properties) | J3, J4 |
| 8 | Copilot panel (generate, edit, claim hovers, copy, mark sent) | J4 |
| 9 | Contacts list + contact form | J4 |
| 10 | Pipeline board + opportunity drawer | J5 |
| 11 | Overview (funnel, signals, my accounts, jobs) | J3, J5 |
| 12 | Activity (jobs, task logs, usage & cost) | J2 |
| 13 | Settings: workspace, members & access, providers, scoring model, audit log | Admin |

**Exit:** you can walk J1–J5 end to end; you approve the visual identity; every screen has designed states; the mock layer matches API_DOCUMENTATION (any contract changes recorded).
**Learning topics:** design tokens, headless UI + accessibility, server-state vs client-state, API contracts and mocking, table virtualisation.

---

## Phase 2 — Backend foundations

Repo + Docker Compose (db, web, worker) · config & logging · Alembic baseline · auth (sessions, invites, CSRF, rate limit) · workspaces, memberships, property access · RLS + isolation tests · properties/offerings/target profile/geocoding · audit log · demo seed (hypothetical property) · CI (lint, types, tests) · OpenAPI → TS client generation; frontend switches Properties + Auth from MSW to real API.

**Exit:** J1 works against the real backend with tests; cross-tenant tests pass.
**Learning:** sessions vs JWT, Argon2, CSRF, RLS, migrations, dependency injection in FastAPI.

---

## Phase 3 — Workflow engine & discovery

`QueueBackend` + `PostgresQueueBackend` · workflow engine (states, leases, retries, idempotency, cancel/resume) · job_events + progress API · providers: CSV, OSM Overpass, Nominatim, web search (coverage test to choose impl), page fetcher with SSRF/robots guards · S1 estimate, S2 plan, S3 discover, S4 resolve, S5 classify · LLM gateway (prompt registry, structured output, cost logging) · CSV import · run screen on real data.

**Exit:** a real job for the hypothetical OMR property discovers and dedupes companies with live progress; killing the worker mid-run and restarting completes without duplicates.
**Learning:** queues & leases, idempotency, backoff, adapter pattern, structured outputs.

---

## Phase 4 — Research, evidence & scoring

S6 research agent (tools, limits, injection defence) · claims & sources persistence · S7 signals (GDELT + extraction) · S8 grounding validator · S9 scoring v1 + versioning · S10 roles · explorer + account page on real data · eval runner + first eval report.

**Exit:** first eval report produced and reviewed; FACT grounding enforced by DB constraint; scores explainable in UI.
**Learning:** agent loops & budgets, grounding/RAG-style verification, deterministic scoring, evaluation methodology.

---

## Phase 5 — Copilot, contacts, pipeline, overview

Contacts CRUD + DNC · C1 copilot + validator + versioning · copy/mark-sent · opportunities + board + activities · overview funnel · activity/usage pages · settings (providers, scoring models, members) · hardening pass (rate limits, headers, error states) · deployment decision + first deploy.

**Exit:** the MVP demo scenario (PRD / v1.0 §2.1) runs end to end on deployed infrastructure.
**Learning:** prompt design for grounded writing, optimistic UI, deployment & migrations in production.

---

## Post-MVP (ordered by expected value; revisit after eval and user feedback)

1. Licensed contact/firmographic provider adapter (+ email verification)
2. Manual merge/split of companies; scheduled re-research & signal alerts
3. Email sending via user's own mailbox (OAuth Gmail/Outlook) with approval, suppression, compliance — after legal review (A-09)
4. Score calibration from outcomes
5. Competitor intelligence
6. Analytics & revenue attribution
7. CRM sync (Salesforce / hotel S&C systems)
8. SSO / managed identity
9. B2C track: Meta Ads (separate product line)
