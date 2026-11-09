# Inhabitr — System Architecture

> Version 1.0 · 2026-11-09 · Related: [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md), [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## 1. Architectural style

**Modular monolith** (D-18): one Python codebase that runs as two process types — the **web app** (FastAPI) and the **worker** — sharing one **PostgreSQL + PostGIS** database, which also serves as the **job queue** (P-02) and **session store** (P-01).

Why: a solo developer needs few moving parts, one deploy, one debugger, one test suite. Module boundaries inside the codebase give most of the benefits of services (separation, testability) without network calls, distributed transactions or extra infrastructure. If a module needs to scale independently later, its boundary makes extraction possible.

**Runtime components (3):** web · worker · Postgres. No Redis, no message broker.

---

## 2. Component diagram

```
                      ┌────────────────────────────────────┐
  Browser             │ React + TS + Vite SPA              │
                      │ TanStack Query · Router · Table    │
                      └───────────────┬────────────────────┘
                                      │ HTTPS · session cookie · CSRF token
                                      ▼
┌──────────────────────────── web (FastAPI, uvicorn) ───────────────────────────┐
│ middleware: request_id · security headers · CSRF · rate limit · session load  │
│ deps: current_user · workspace scope (sets RLS var) · permission checks       │
│ routers /api/v1: auth · properties · discovery · imports · companies ·        │
│                  accounts · contacts · copilot · opportunities · activities · │
│                  activity · admin · eval                                      │
│ services (domain logic) ── repositories (SQLAlchemy) ── Postgres              │
│ enqueue via QueueBackend (same DB transaction as domain writes)               │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
                     ┌──────────────────▼──────────────────┐
                     │ PostgreSQL 16 + PostGIS              │
                     │ domain tables · workflow_tasks ·     │
                     │ queue tables · sessions · logs       │
                     └──────────────────▲──────────────────┘
                                        │ claim task (SKIP LOCKED / lease)
┌───────────────────────────────────────┴───────────────────────────────────────┐
│ worker (same codebase)                                                        │
│ WorkflowEngine → StepRegistry → Step.run(ctx, input) → output                 │
│   BudgetGuard · RetryPolicy · TaskLease · structured logging                  │
│ Adapters (providers/):                                                        │
│   LLMGateway(OpenAI | …) · SearchProvider(Tavily|Brave|Exa) · OSMOverpass ·   │
│   Geocoder(Nominatim) · PageFetcher(httpx → Playwright fallback) · GDELT ·    │
│   GooglePlaces (optional, off) · CSVReader                                    │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Backend module layout

```
backend/
  app/
    main.py                 # FastAPI app factory
    worker.py               # worker entrypoint
    core/                   # config (pydantic-settings), db session, logging, errors,
                            # security (hashing, crypto), tenancy (RLS), pagination
    auth/                   # sessions, invites/reset tokens, roles, permission deps
    workspaces/             # workspace settings, memberships, property access
    properties/             # properties, offerings, target profiles, geocoding
    companies/              # companies, locations, identifiers, sources, claims, signals,
                            # entity resolution
    accounts/               # account status, scoring, saved views, export, roles recs
    contacts/
    discovery/              # jobs, DiscoveryConfig, NL parsing, estimation, workflow def
    imports/                # CSV import
    workflow/               # engine, step registry, task state machine, budgets, retries
    queue/                  # QueueBackend interface + PostgresQueueBackend
    providers/              # adapter interfaces + implementations + registry
    llm/                    # gateway, prompt registry, structured output, cost table
      prompts/              # versioned prompt files (YAML/Jinja)
    copilot/
    pipeline/               # opportunities, activities
    activity/               # job views, usage/cost views, audit log
    eval/                   # dataset loader, runner, metrics
    seed/                   # demo workspace seed
  migrations/               # Alembic
  tests/                    # unit/, integration/, workflow/, security/, eval/
```

**Module rules**
1. Each module exposes a `service.py` (public functions) and `schemas.py` (Pydantic I/O). Other modules call services, never another module's repositories/tables directly.
2. Routers are thin: parse → call service → return schema.
3. Domain logic is framework-free where practical (testable without HTTP).
4. Cross-cutting concerns (tenancy, logging, errors) live in `core/`.

---

## 4. Request lifecycle (web)

1. `request_id` middleware assigns/propagates `X-Request-ID`.
2. Session middleware reads cookie → hashes token → loads `sessions` row → user, active workspace.
3. CSRF check on unsafe methods (double-submit: `X-CSRF-Token` header must match the session's CSRF token).
4. Dependency `workspace_scope` opens a DB transaction and runs `SET LOCAL app.workspace_id = '<uuid>'` (and `app.user_id`) so **RLS policies** apply to every query.
5. Permission dependency checks role and property access.
6. Service executes; errors raise typed `AppError` subclasses → mapped to RFC 9457 problem+json.
7. Structured log line with request_id, user_id, workspace_id, route, status, latency.

---

## 5. Authentication & authorization (P-01)

| Concern | Design |
|---|---|
| Passwords | Argon2id (`argon2-cffi`), parameters from config; rehash on login if params change |
| Sessions | Random 256-bit token in cookie; **only SHA-256 hash stored** in `sessions`; idle 7 d / absolute 30 d; revocable |
| Cookie | `__Host-inhabitr_session`, HttpOnly, Secure, SameSite=Lax, Path=/ |
| CSRF | Per-session CSRF token returned by `/auth/me`; required in `X-CSRF-Token` for POST/PATCH/PUT/DELETE |
| Invites / reset | `auth_tokens` (purpose `invite`/`password_reset`), hashed, single-use, expiring. MVP: Admin copies the link (no email infra) |
| Brute force | Rate limit login per IP+email; generic error messages; audit failures |
| Roles | `admin`, `manager`, `rep` per membership |
| Property access | Admin/Manager: all properties in workspace; Rep: rows in `property_access` |
| Enforcement | (1) permission dependencies in routers, (2) service-level scoping by property, (3) **Postgres RLS by workspace** as defence in depth |
| Future | Managed IdP / SSO replaces `auth/` login only; sessions and permissions stay |

SPA and API are served from the **same site** (API under `/api`) so cookies work without cross-site complexity. In dev, Vite proxies `/api` to FastAPI.

---

## 6. Multi-tenancy

- Every tenant-owned table has `workspace_id NOT NULL`.
- RLS policy on each: `USING (workspace_id = current_setting('app.workspace_id')::uuid)`.
- The application connects as a non-owner role (RLS applies); migrations run as owner.
- Worker tasks carry `workspace_id`; the engine sets the same session variable before running a step.
- Tests: a dedicated suite tries cross-workspace reads/writes through API and raw SQL and must see nothing.

---

## 7. Workflow engine & queue (P-02)

### 7.1 Separation of concerns

| Layer | Responsibility | Swappable? |
|---|---|---|
| **Workflow engine** (`workflow/`) | Job & task state machines, step ordering, fan-out per company, budgets, retries policy, progress counts, resume/cancel | No — core domain |
| **QueueBackend** (`queue/`) | Deliver "run task X" messages to workers; delayed retries; leases | **Yes** — Postgres now; Celery/Temporal later |
| **Steps** (`discovery/steps/…`) | Pure-ish units of work with typed input/output | Added by registration |

`QueueBackend` interface:

```python
class QueueBackend(Protocol):
    def enqueue(self, task_id: UUID, *, run_after: datetime | None = None,
                priority: int = 0, conn: Connection) -> None: ...   # same txn as domain write
    def claim(self, worker_id: str, limit: int) -> list[UUID]: ...   # leased
    def heartbeat(self, task_id: UUID, worker_id: str) -> None: ...
    def ack(self, task_id: UUID) -> None: ...
    def nack(self, task_id: UUID, *, retry_at: datetime | None) -> None: ...
```

MVP implementation: `PostgresQueueBackend` using a `queue_items` table and `SELECT … FOR UPDATE SKIP LOCKED` with lease expiry. (Procrastinate is an acceptable drop-in implementation behind the same interface; decision at Phase 3 — see DECISION_LOG P-02 note.)

**Source of truth = `workflow_tasks` + `discovery_jobs`.** The queue only says "go run task X". If the queue were wiped, a reconciler could re-enqueue every `pending`/expired-`running` task from `workflow_tasks`.

### 7.2 State machines

```
discovery_jobs.status
  queued ─► running ─┬─► completed
                     ├─► completed_with_errors
                     ├─► failed            (cannot proceed: e.g. no sources configured, plan step failed)
                     ├─► paused_budget ─► running (budget raised) / completed_with_errors (finish)
                     └─► cancelling ─► cancelled

workflow_tasks.status
  pending ─► running ─┬─► succeeded
                      ├─► failed_retryable ─► pending (run_after = backoff)
                      ├─► failed            (attempts exhausted or non-retryable)
                      ├─► skipped           (cancelled / upstream filtered)
                      └─► blocked_budget    (resumes as pending if budget raised)
```

### 7.3 Execution model

- Job-level steps (plan, discover per provider, resolve, classify) run once per job.
- Per-company steps (research → signals → ground → score → roles) run as a **chain per company**; companies run in parallel up to `max_concurrency`.
- When a step succeeds, the engine (in the same transaction as writing the step output) creates and enqueues the next task(s). This makes progress **resumable**: there is no in-memory workflow state.
- **Idempotency:** each task has `idempotency_key = f"{job_id}:{step}:{subject_id}"` (unique). Steps write with upserts keyed on natural keys (e.g. claims superseded by `(company_id, field, produced_by_task_id)`), so a re-run after a crash replaces rather than duplicates.
- **Leases:** a running task has `lease_expires_at`; workers heartbeat every 15 s; expired leases are reclaimed and retried.
- **Cancel:** sets `cancel_requested`; engine stops enqueuing; pending tasks → `skipped`; running tasks finish.
- **Resume:** re-enqueues `pending`, `blocked_budget`, and optionally `failed` tasks (Retry failed).

### 7.4 Retries & error classification

| Error class | Examples | Policy |
|---|---|---|
| `TransientError` | timeouts, 429, 5xx, connection reset | retry with exponential backoff + jitter (base 5 s, ×2, max 5 min), max 4 attempts; respect `Retry-After` |
| `ProviderQuotaError` | provider daily quota exhausted | pause provider for job; mark tasks `failed_retryable` with long delay |
| `ValidationError` | LLM output fails schema after repair attempt | 1 repair retry with error feedback, then `failed` |
| `BudgetExceeded` | next call would exceed cap | task `blocked_budget`, job `paused_budget` |
| `PermanentError` | 404 site, robots disallow, bad input | `failed` (no retry), reason shown in UI |
| Unknown exception | bug | `failed`, Sentry event, stack in logs (not UI) |

### 7.5 Progress API & polling (P-05)

`GET /discovery/jobs/{id}` returns job status, per-stage counts (`pending/running/succeeded/failed`), cost-so-far, budget, recent events, and a cursor for newly scored accounts. The SPA polls every 2 s while running (TanStack Query `refetchInterval`), 0 when terminal. A `job_events` stream table (append-only) backs both polling now and **SSE later** (an SSE endpoint would tail the same table — no engine change).

---

## 8. Provider adapters (P-06, configurable)

### 8.1 Interfaces

```python
class DiscoveryProvider(Protocol):
    key: str                       # "osm", "web_search", "google_places", "csv"
    license: LicensePolicy         # storage TTL, attribution, exportable, cross-tenant
    def estimate(self, cfg: DiscoveryConfig) -> ProviderEstimate: ...
    def discover(self, cfg: DiscoveryConfig, ctx: StepContext) -> list[RawCandidate]: ...

class SearchProvider(Protocol):
    def search(self, query: str, *, max_results: int, ctx: StepContext) -> list[SearchResult]: ...

class PageFetcher(Protocol):
    def fetch(self, url: str, ctx: StepContext) -> FetchedPage: ...   # text, title, hash, status

class NewsProvider(Protocol):
    def find(self, company: CompanyRef, since: date, ctx: StepContext) -> list[NewsItem]: ...

class Geocoder(Protocol):
    def geocode(self, address: str) -> list[GeoResult]: ...

class LLMProvider(Protocol):          # used only via LLMGateway
    def complete_structured(self, req: StructuredRequest) -> StructuredResponse: ...
    def complete_with_tools(self, req: ToolLoopRequest) -> ToolLoopTurn: ...
```

`StepContext` carries workspace_id, job_id, task_id, logger, `BudgetGuard`, and a `CostRecorder`. **Every adapter call goes through BudgetGuard and is recorded in `provider_calls` / `llm_calls`.**

### 8.2 Registry & configuration

- Adapters register with `@provider("web_search", impl="tavily")`.
- Config resolution: environment defaults → workspace settings (`provider_credentials.config`) → per-job selection.
- Each provider config: `enabled`, `impl`, `api_key` (encrypted), `rate_limit`, `unit_prices`, `daily_cap`.
- **Google Places**: disabled by default; when enabled, its `LicensePolicy` enforces storage rules (keep `place_id`, refresh/expire other content per current Google terms — verified at enablement time).

### 8.3 MVP adapters

| Adapter | Impl | Cost | Notes |
|---|---|---|---|
| CSV | built-in | free | |
| OSM | Overpass API | free | ODbL attribution in UI footer of map/explorer; respect public instance usage policy (or self-host later) |
| Geocoder | Nominatim | free | usage policy: ≤1 req/s, identify app via generic User-Agent; cache results |
| Web search | Tavily / Brave / Exa (chosen in Phase 3 coverage test) | low | |
| Page fetch | httpx + readability extraction; Playwright fallback when page is JS-only | free (compute) | robots.txt, 10 s timeout, 2 MB cap, SSRF guard |
| News | GDELT DOC API | free | publish dates from GDELT metadata |
| Places | Google Places API (New) | paid beyond free usage | off by default |

### 8.4 Fetch safety (SSRF & politeness)

Resolve DNS and block private/loopback/link-local/metadata IP ranges; only http/https; max 3 redirects (re-check each); per-domain rate limit (1 req/s); robots.txt cached 24 h; no cookies/auth; content-type allow-list (HTML, plain text, PDF later); size and time limits.

---

## 9. Cost estimation, budgets & execution limits

Detailed formulas in [AGENT_ARCHITECTURE.md §9](AGENT_ARCHITECTURE.md#9-budgets-cost-estimation-and-execution-limits). System-level mechanics:

- **Price table** (`llm/pricing.yaml`, `providers/pricing.yaml`): per model input/output token prices and per provider unit prices. Config, not code; updated when vendor prices change.
- **BudgetGuard.reserve(estimated_cost)** before each call; **commit(actual_cost)** after. If `spent + reserved + estimate > budget`, raise `BudgetExceeded`.
- **Execution limits** (defaults, configurable per workspace): max companies per job 200; max concurrency 5; per-company research caps (see agent doc); job wall-clock cap 3 h; LLM call timeout 60 s; fetch timeout 10 s.
- **Estimate accuracy loop:** after each job, actual per-company averages are stored and used for future estimates.

---

## 10. Logging, errors & observability

- **structlog** JSON logs; every line has `request_id` or `job_id`/`task_id`/`step`, `workspace_id`.
- **Error tracking:** Sentry SDK (DSN optional via env; disabled locally).
- **LLM observability:** `llm_calls` table (model, prompt id+version, tokens, cost, latency, status, error). Full prompt/response bodies stored only when `LLM_DEBUG_CAPTURE=true`, with 14-day retention.
- **Job events:** `job_events` for user-facing progress messages (never stack traces).
- **Audit:** `audit_logs` for security-relevant actions (PRD FR-1.5).
- **Health:** `/healthz` (process) and `/readyz` (DB reachable, migrations current); worker writes heartbeat to `worker_heartbeats`.

---

## 11. Frontend architecture

| Concern | Choice |
|---|---|
| Build | Vite + React 18 + TypeScript (strict) |
| Routing | React Router (data routers) |
| Server state | TanStack Query (caching, polling, optimistic updates) |
| Tables | TanStack Table (headless) + virtualised rows (TanStack Virtual) |
| UI primitives | Radix UI primitives (accessibility) + our own components |
| Styling | **CSS Modules** + central **design tokens** (CSS custom properties in `design/tokens.css`), light & dark themes via `[data-theme]` (D-21) |
| Forms | React Hook Form + Zod |
| Maps | MapLibre GL + OSM-derived tiles (attribution shown) |
| Charts | Small set (funnel, bar, sparkline) — library chosen in Phase 1 |
| Icons | Lucide (consistent stroke icon set) |
| API client | Generated from OpenAPI (`openapi-typescript` + thin fetch wrapper) |
| Mocking (Phase 1) | **Mock Service Worker (MSW)** implementing the documented API contract with typed fixtures (P-09, accepted); enabled only when `VITE_API_MOCKING=on` |
| Testing | Vitest + Testing Library (components), Playwright (E2E journeys) |

```
frontend/src/
  app/            # providers, router, layout shell
  design/         # tokens.css, theme, typography, primitives (Button, Badge, …)
  components/     # composed components (EvidenceChip, ScoreBar, RunTimeline, DataTable…)
  features/       # properties/, discovery/, accounts/, contacts/, copilot/, pipeline/,
                  # overview/, activity/, settings/, auth/
  api/            # generated types, client, query hooks
  mocks/          # MSW handlers + fixtures (all fixture records carry data_origin: "mock")
  lib/            # formatters (INR, dates, distance), utils
```

**Why MSW for the prototype:** the prototype calls the *same* API client and hooks the real app will use; MSW intercepts requests in the browser and returns fixtures. Moving to the real backend = turning MSW off. The prototype also becomes an executable spec of the API.

---

## 12. Deployment

| Environment | Setup |
|---|---|
| Local | Docker Compose: `db` (postgis/postgis:16), `web` (uvicorn --reload), `worker`, `frontend` (Vite dev server proxying `/api`) |
| Production (decide Phase 5) | One container host running `web` and `worker` images; managed Postgres with PostGIS; SPA built and served by the web container (or CDN) under the same domain; TLS by platform |
| CI | GitHub Actions (or equivalent): lint (ruff, eslint), type check (mypy, tsc), tests (pytest with Postgres service, vitest), build images, run migrations check |

**Configuration** via environment (pydantic-settings): `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, `OPENAI_API_KEY`, `SEARCH_PROVIDER`, `SEARCH_API_KEY`, `GOOGLE_PLACES_ENABLED=false`, `SENTRY_DSN`, `APP_BASE_URL`, `LOG_LEVEL`, `LLM_DEBUG_CAPTURE`, limit defaults. `.env.example` documents all.

**Migrations:** Alembic; run as a release step before web/worker start; never auto-generate without review.

**Backups:** managed Postgres daily backups + point-in-time recovery where available.

---

## 13. Security architecture summary

| Threat | Control |
|---|---|
| Cross-tenant data leak | App scoping + RLS + isolation tests |
| Session theft | HttpOnly/Secure cookies, hashed tokens, revocation, short idle timeout |
| CSRF | SameSite=Lax + double-submit token |
| Credential stuffing | Rate limits, Argon2id, audit |
| Secret leakage | Env secrets, encrypted provider keys, never in responses/logs (log scrubbing) |
| Prompt injection via web content | Read-only tools, content delimiting, schema + grounding validation, no side-effect tools |
| SSRF via fetcher | IP-range blocking, scheme allow-list, redirect re-validation |
| Over-collection of personal data | Role-level targeting; manual contacts with source note; do-not-contact; retention limits; DPDP legal review before real customers (A-09) |
| Provider ToS breach | `LicensePolicy` per source; Places off by default; robots.txt |
| Injection (SQL/XSS) | ORM parameterisation; React escaping; markdown rendered via sanitiser; CSP header |

---

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Thin public data on Indian mid-market (A-02) | Eval early; honest UNKNOWN; CSV path; paid adapter slot |
| Hallucinated facts | Claims model + grounding validator + copilot restricted to FACTs |
| Entity resolution errors | Identifier-first matching; geo proximity; manual merge/split (post-MVP UI; DB supports `merged_into_id`) |
| Geography (registered vs operating address; corridor shape) | Prefer operating locations; distance decay rather than hard cut |
| Cost overrun | Estimates, caps, cheap models for bulk steps, on-demand copilot |
| Postgres queue limits | Fine for our volume (≪ 100 tasks/s); `QueueBackend` abstraction allows Celery/Temporal |
| Solo-developer bus factor | Docs, decision log, typed code, tests, small modules |

---

## 15. Configurable business rules (D-22)

Business rules are data, not literals scattered through code:

| Kind of rule | Home | Changed by |
|---|---|---|
| Scoring weights, curves, thresholds, signal half-lives | `scoring_models` (versioned rows) | Admin → new version → explicit rescore |
| Workspace limits, budgets, retention, locale | `workspaces.settings` (validated Pydantic model, defaults from config) | Admin settings |
| Platform security & system defaults (session TTLs, grounding thresholds, research depths, estimate multipliers) | `core/config.py` (pydantic-settings, env-overridable) | Deploy config |
| Fixed vocabularies (statuses, reasons, offerings, signal types) | Backend `StrEnum` → OpenAPI → generated TS types | Code change + migration + DECISION_LOG entry |

Every entry is listed in the DECISION_LOG defaults register (DD-xx) with its location. Frontend never re-implements these rules: it displays what the API returns (e.g. tiers and breakdowns come from the backend, the UI does not recompute them).
