# Inhabitr — Decision Log

> Format: each entry has an ID, date, status, decision, context/why, alternatives, consequences.
> Status values: **Confirmed** (owner decision) · **Accepted** (proposal approved by owner) · **Design default** (made while writing docs; stands unless owner objects) · **Proposed** (awaiting owner) · **Superseded**.
> Assumptions are tracked separately at the end — they are *not* decisions.

---

## Confirmed decisions (owner)

| ID | Date | Decision | Why / notes |
|---|---|---|---|
| D-01 | 2026-11-09 | Real trial project with Inhabitr; working, demonstrable, potentially commercial; built for deep understanding | Sets quality bar between demo and production |
| D-02 | 2026-11-09 | Initial market: pre-opening hotels; model supports operating hotels (`properties.lifecycle`) | Sharpest pain, clear urgency |
| D-03 | 2026-11-09 | India-first | Drives data sources, compliance (DPDP), currency/timezone defaults |
| D-04 | 2026-11-09 | Free/low-cost sources first; paid via configurable adapters; cost estimate before costly jobs | Budget realism |
| D-05 | 2026-11-09 | OpenAI first behind an LLM provider abstraction | Owner preference; swappable |
| D-06 | 2026-11-09 | Outreach = drafts only (edit, copy, mark sent); no automated sending in MVP | Compliance & deliverability risk deferred |
| D-07 | 2026-11-09 | Independent pipeline + CSV import/export; CRM integration later | Avoid integration dependency |
| D-08 | 2026-11-09 | Solo primary developer; modular, documented codebase | Drives simplicity choices |
| D-09 | 2026-11-09 | "Inhabitr" is a working name pending trademark clearance | Keep brand in config/tokens |
| D-10 | 2026-11-09 | Role-level targeting + manual contacts; licensed provider later | Legality & accuracy of contact data |
| D-11 | 2026-11-09 | Deterministic workflow; one bounded research agent where autonomy is needed | Reliability, cost, testability |
| D-12 | 2026-11-09 | Separate Fit / Intent / Confidence / Actionability | Opportunity ≠ reachability ≠ trust |
| D-13 | 2026-11-09 | Companies tenant-scoped | Prevent cross-tenant leakage; provider licences |
| D-14 | 2026-11-09 | Lead (Account) = Company × Property | Same company, different value per hotel |
| D-15 | 2026-11-09 | CSV import from day one | Teams already have lists |
| D-16 | 2026-11-09 | Excellent enterprise UX is a top priority; premium, Linear/Attio-inspired, distinct identity | Adoption depends on it |
| D-17 | 2026-11-09 | Out of MVP: Meta Ads, B2C, automated email, LinkedIn automation | Focus |
| D-18 | 2026-11-09 | Modular monolith: React/TS/Vite + FastAPI + PostgreSQL/PostGIS | Solo-friendly |
| D-19 | 2026-11-09 | Test first with a hypothetical property + manually validated dataset | No hotel partner yet |

## Accepted proposals

| ID | Date | Decision | Notes |
|---|---|---|---|
| P-01 | 2026-11-09 | Built-in session auth: Argon2id, Postgres-backed sessions, Secure/HttpOnly/SameSite cookies, invite-only | See SYSTEM_ARCHITECTURE §5 |
| P-02 | 2026-11-09 | Postgres-backed queue instead of Redis/Celery, **behind a `QueueBackend` abstraction** enabling later Celery/Temporal | Transactional enqueue; one fewer service. Implementation choice (own `SKIP LOCKED` worker vs Procrastinate) to be made at Phase 3 start — both fit the interface |
| P-03 | 2026-11-09 | Terminology: Workspace, Property, Company, Account, Contact, Opportunity | Glossary in PROJECT_OVERVIEW §6 |
| P-04 | 2026-11-09 | Two lifecycles: Account prospecting status vs Opportunity stages | DATABASE_SCHEMA §3.4, §3.7 |
| P-05 | 2026-11-09 | Polling for progress; architecture allows SSE later (`job_events` table) | |
| P-06 | 2026-11-09 | Sources: CSV, OSM, web search, website fetch, GDELT; Google Places optional & off by default | |
| P-07 | 2026-11-09 | Copilot outputs on demand per account | Cost control |
| P-08 | 2026-11-09 | Seeded demo workspace with hypothetical OMR property; demo vs real always distinguishable (`is_demo`, `is_hypothetical`, `data_origin`) | DATABASE_SCHEMA §6 |
| P-09 | 2026-11-09 | Phase 1 prototype uses **Mock Service Worker (MSW)** implementing the documented API contract, consumed through the same typed API client and hooks the real app will use. Mock handlers and fixtures live only in `frontend/src/mocks/`; switching to FastAPI = setting `VITE_API_MOCKING=off` | Owner requirements: same client & contracts, mocks isolated from app logic, minimal switch-over, realistic loading/empty/error/success/partial states |
| P-10 | 2026-11-09 | Frontend: React + TS + Vite, TanStack Query/Table/Virtual, React Router, React Hook Form + Zod, Radix UI primitives, MapLibre, Lucide. **Modified by owner: no Tailwind** — see D-21 | |

## Confirmed decisions (continued)

| ID | Date | Decision | Why / notes |
|---|---|---|---|
| D-20 | 2026-11-09 | **Evaluation reference is fixed:** one reference pin (recorded in `data/eval/README.md`) and a 15 km radius for all eval runs; changing either creates a new dataset version (`ground_truth_omr_v2`), never edits v1 | Makes eval results comparable over time |
| D-21 | 2026-11-09 | **Styling = CSS Modules + a central design-token system (CSS custom properties)** for colour, type, spacing, radii, borders, shadows, motion and themes. No Tailwind. Screens compose reusable components; screen-level CSS is limited to layout | Owner preference: polished, consistent, maintainable for a solo developer |
| D-22 | 2026-11-09 | **No silently hard-coded business rules.** Every default affecting product behaviour, scoring, security or data handling is (a) listed in the defaults register below with its owning config location, and (b) read from config (`core/config.py` settings, workspace `settings`, or versioned `scoring_models`), not literals in logic | Owner instruction; keeps rules reviewable and changeable |
| D-23 | 2026-11-09 | Design defaults DD-01…DD-16 accepted as initial defaults (revisitable) | |

## Defaults register (DD-xx)

> Accepted as initial defaults (D-23). **Impact** flags the defaults the owner asked to track: **B** = product behaviour, **S** = scoring, **Sec** = security, **D** = data handling, **T** = technical only.
> **Lives in** = where the value is defined. Values marked *config* must never be duplicated as literals in code.

| ID | Default | Impact | Lives in | Spec |
|---|---|---|---|---|
| DD-01 | UUIDv7 primary keys | T | code (model base) | DATABASE_SCHEMA §1 |
| DD-02 | Enums as `text + CHECK`, mirrored in Python `StrEnum` / TS unions | T | code + migrations | DATABASE_SCHEMA §1 |
| DD-03 | Notes stored as `activities` of type `note` | T | schema | DATABASE_SCHEMA §3.7 |
| DD-04 | Admin & Manager see all properties; Reps see assigned properties only | **Sec, B** | `auth/permissions.py` single policy table (one place) | PRD FR-1.3 |
| DD-05 | Inaccessible resources return 404, not 403 | **Sec** | `core/errors.py` mapping | API §1 |
| DD-06 | SPA and API on the same site; Vite proxy in dev | **Sec** | deployment config | SYSTEM_ARCHITECTURE §5 |
| DD-07 | Geocoding via OSM Nominatim (usage policy respected), manual pin override | **D** | config `GEOCODER_PROVIDER` | PRD FR-2.2 |
| DD-08 | Invite/reset links shown to Admin to share manually; TTL invite 72 h, reset 1 h | **Sec** | config `INVITE_TTL_HOURS`, `RESET_TTL_MINUTES` | SYSTEM_ARCHITECTURE §5 |
| DD-09 | Scoring v1: Fit = industry 30 / inbound travel 30 / proximity 20 / scale 20; Priority = 0.6 Fit + 0.4 Intent; tiers A ≥ 65, B 45–64, C < 45 | **S** | `scoring_models.weights` (versioned, DB) | AGENT_ARCHITECTURE §8 |
| DD-10 | Scale curve peaks at 201–1000 employees | **S** | `scoring_models.params.scale_curve` | AGENT_ARCHITECTURE §8.1 |
| DD-11 | Signal window 365 days; per-type strengths and half-lives; intent saturation 1.5 | **S** | `scoring_models.params.signals` (+ `DiscoveryConfig.signal_window_days`) | AGENT_ARCHITECTURE §6 |
| DD-12 | Grounding: exact match, else fuzzy ≥ 92 (`passed_fuzzy`), else downgrade to unknown; >3-year-old sources halve confidence | **D, S** | config `GROUNDING_FUZZY_THRESHOLD`, `GROUNDING_STALE_YEARS`; value recorded per claim in `grounding_detail` | AGENT_ARCHITECTURE §7 |
| DD-13 | Retention: page text 90 d, LLM debug payloads 14 d, job events 180 d, audit 2 y | **D** | workspace `settings.retention.*` (defaults in config) | DATABASE_SCHEMA §7 |
| DD-14 | Research `fetch_page` restricted to URLs from search results / company domain | **Sec** | code policy (intentionally *not* configurable) | AGENT_ARCHITECTURE §5.1 |
| DD-15 | Currency INR, timezone Asia/Kolkata | B | workspace `settings.locale` | PRD NFR-14 |
| DD-16 | Max companies/job 200; concurrency 5; job wall-clock 3 h | **B** | workspace `settings.limits.*` (defaults in config) | SYSTEM_ARCHITECTURE §9 |
| DD-17 | Sessions: idle 7 d, absolute 30 d; login rate limit 5/min per IP+email | **Sec** | config `SESSION_IDLE_DAYS`, `SESSION_ABSOLUTE_DAYS`, `LOGIN_RATE_LIMIT` | PRD FR-1.2 |
| DD-18 | Per-company research caps (standard: 8 tool calls / 6 pages / $0.15; light: 4 / 2 / $0.05) — placeholder $ values until measured | **B** | config `RESEARCH_DEPTHS` | AGENT_ARCHITECTURE §5.5, §9.3 |
| DD-19 | Dismiss reasons and loss reasons are fixed lists | B | shared enum (backend `StrEnum` → OpenAPI → TS) | PRD FR-8.8, FR-11.4 |
| DD-20 | Classification batch 20; estimate multipliers ×0.6/×1/×1.8 until history exists; pass rate 0.5 | B | config `DISCOVERY_ESTIMATE_*` | AGENT_ARCHITECTURE §9.2 |

## Open items (decide later, at the phase noted)

| Item | Decide at |
|---|---|
| Web search provider (Tavily / Brave / Exa) — coverage test on eval companies; verify current pricing/terms | Phase 3 start |
| Queue implementation (own SKIP LOCKED vs Procrastinate) behind `QueueBackend` | Phase 3 start |
| Models per tier (`fast`, `standard`) — from eval quality & cost | Phase 3–4 |
| Production hosting (needs managed Postgres + PostGIS) | Phase 5 |
| Chart library | Phase 1 |
| Visual identity (palette, typography, density) | Phase 1 step 1 — proposal in `docs/DESIGN_SYSTEM.md`, awaiting owner review |

---

## Assumptions register

> These require real-world validation. Status: **Open** · **Validated** · **Invalidated**.

| ID | Assumption | Validation method | If false | Status |
|---|---|---|---|---|
| A-01 | Pre-opening sales teams will use an AI-ranked account list | Demo/interview any reachable hotel sales professional | Reposition as research assistant on their own lists (CSV-first) | Open |
| A-02 | Free/low-cost public data gives useful research on OMR mid-market firms | Eval: % companies with ≥ 5 grounded FACT claims | Paid firmographic provider earlier | Open |
| A-03 | OSM + web search discover enough relevant companies without Places | Eval: recall per source | Enable Places adapter | Open |
| A-04 | Signals for mid-market Indian firms are findable and datable | Eval: % with ≥ 1 dated signal < 12 months | Intent weight reduced | Open |
| A-05 | Inbound-travel features predict hotel demand | Expert review; later outcomes | Revise Fit features | Open |
| A-06 | Initial weights are sensible | Ranking agreement with expert; later outcome calibration | Recalibrate | Open |
| A-07 | Research cost per company is acceptable | Measured cost on eval run | Light depth, cheaper models, caching | Open |
| A-08 | Role-level targeting + manual contacts makes a convincing demo | Demo feedback | Pull licensed provider forward | Open |
| A-09 | A compliant legal position on storing named business contacts (India DPDP Act) exists before commercial use | Legal review before first real customer | Restrict contact storage/processing | Open |
| A-10 | "Inhabitr" usable as product name | Trademark check | Rename (brand isolated in config/tokens) | Open |
