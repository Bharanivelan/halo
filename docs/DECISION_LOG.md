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
| D-05 | 2026-11-09 | OpenAI first behind an LLM provider abstraction | Owner preference; swappable. **Superseded by D-32** |
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
| P-09 | 2026-11-09 | ~~Superseded by D-24.~~ Phase 1 prototype uses **Mock Service Worker (MSW)** implementing the documented API contract, consumed through the same typed API client and hooks the real app will use. Mock handlers and fixtures live only in `frontend/src/mocks/`; switching to FastAPI = setting `VITE_API_MOCKING=off` | Owner requirements: same client & contracts, mocks isolated from app logic, minimal switch-over, realistic loading/empty/error/success/partial states |
| P-10 | 2026-11-09 | Frontend: React + TS + Vite, TanStack Query/Table/Virtual, React Router, React Hook Form + Zod, Radix UI primitives, MapLibre, Lucide. **Modified by owner: no Tailwind** — see D-21. **For the new Lovable app (halo-web) superseded by D-34**; still applies to halo-web-classic | |

## Confirmed decisions (continued)

| ID | Date | Decision | Why / notes |
|---|---|---|---|
| D-20 | 2026-11-09 | **Evaluation reference is fixed:** one reference pin (recorded in `data/eval/README.md`) and a 15 km radius for all eval runs; changing either creates a new dataset version (`ground_truth_omr_v2`), never edits v1 | Makes eval results comparable over time |
| D-21 | 2026-11-09 | **Styling = CSS Modules + a central design-token system (CSS custom properties)** for colour, type, spacing, radii, borders, shadows, motion and themes. No Tailwind. Screens compose reusable components; screen-level CSS is limited to layout | Owner preference: polished, consistent, maintainable for a solo developer |
| D-22 | 2026-11-09 | **No silently hard-coded business rules.** Every default affecting product behaviour, scoring, security or data handling is (a) listed in the defaults register below with its owning config location, and (b) read from config (`core/config.py` settings, workspace `settings`, or versioned `scoring_models`), not literals in logic | Owner instruction; keeps rules reviewable and changeable |
| D-23 | 2026-11-09 | Design defaults DD-01…DD-16 accepted as initial defaults (revisitable) | |
| D-24 | 2026-11-09 | **Roadmap change (owner): build the real product now** for a CEO demo, on real public data, instead of a mock-data prototype first. Phases 1–5 are delivered together as a working vertical slice. **P-09 (MSW) superseded**: the frontend talks to the real API; `frontend/src/api/types.ts` is the contract | Owner instruction "get this implemented for real" |
| D-25 | 2026-11-09 | Research agent v1: homepage fetched deterministically, then a bounded tool loop (`fetch_page`, `web_search` when configured, `finish`) with per-company caps on calls, pages and cost; claims submitted via `finish` and grounded on write | Saves one model turn per company; same safety properties as AGENT_ARCHITECTURE §5 |
| D-26 | 2026-11-09 | Every AI-backed step has a deterministic fallback (OSM-tag classification, keyword signals, template drafts) so the pipeline runs without an API key | Principle "AI-first, not AI-dependent" |
| D-27 | 2026-11-09 | Companies beyond `max_companies` are kept and scored from basic data (not researched) rather than dropped; users can research them individually | No discovered data is wasted; research spend stays capped |
| D-28 | 2026-11-09 | ORM models live in one module (`backend/app/models.py`) rather than per domain module | Simpler for a solo developer; domain modules still own their logic |
| D-29 | 2026-11-09 | Grounding validation runs when each claim/signal is written (inside research/signals) rather than as a separate pipeline step; the UI shows it as part of "Scoring & validating evidence" | Simpler; same guarantee (DB constraint on FACT claims) |
| D-30 | 2026-11-09 | Public data services are used politely: Overpass endpoints rotate with backoff; GDELT throttled to 1 request / 5.5 s and treated as best-effort; Nominatim ≤ 1 req/s with caching; websites 1 req/s per domain with robots.txt | Their usage policies; reliability |
| D-31 | 2026-11-09 | Job-row locking uses `FOR NO KEY UPDATE` (fixes a deadlock found in testing between concurrent task completions) and DB operational errors are retried as transient | Found during end-to-end test |
| D-32 | 2026-11-09 | Gemini is the default AI provider (`LLM_PROVIDER=gemini`, default model `gemini-2.5-flash`), called through Google's OpenAI-compatible endpoint so the gateway, tool-calling research loop, budget guard and cost log are unchanged. OpenAI remains selectable with `LLM_PROVIDER=openai`. Gemini thinking tokens are counted as output for cost; reasoning effort set to low; Gemini tool-call "thought signatures" are echoed back. Prices in config are placeholders to verify | Owner request |
| D-33 | 2026-11-10 | Product name **Halo** (by Inhabitr). Inhabitr stays the company brand. Internal identifiers (DB names, Python package) keep `inhabitr` to avoid churn | Owner choice; motif = the catchment "halo" around each location |
| D-34 | 2026-11-10 | The main web app is rebuilt in **Lovable** (React + Tailwind + shadcn/ui, Lovable's stack) against the existing API, using a prompt pack + typed API kit in `docs/lovable/`. Supersedes the no-Tailwind rule (P-10/D-21) for that app only. No Supabase/Lovable Cloud: the API remains the single source of data and logic | Owner wants a more striking UI for the CEO demo, faster |
| D-35 | 2026-11-10 | Backend and frontend are **separate repos**: `halo-api` (this repo: API, worker, DB, docs) and `halo-web` (Lovable, synced to GitHub). The first React UI moved to a sibling folder/repo `halo-web-classic` as a fallback | Owner request; Lovable must own its repo |
| D-36 | 2026-11-10 | **Bearer-token sessions** for frontends on another site: `POST /auth/login` with `X-Auth-Mode: token` returns `access_token` (same server-side session row, expiry and revocation as cookies). Bearer requests skip CSRF (not sent automatically by browsers). CORS allows Lovable domains via `CORS_ORIGIN_REGEX`. Token kept in localStorage in halo-web (XSS exposure accepted for demo; revisit before customers) | Cross-site cookies are blocked by many browsers |
| D-37 | 2026-11-10 | Demo reachability via a **tunnel** to the local API (`scripts/tunnel.ps1`): ngrok with a free static domain preferred (stable URL); Cloudflare quick tunnel as fallback. trycloudflare.com is blocked by this machine's Wi-Fi DNS. Anyone with the URL reaches the login and API docs; data still needs sign-in; stop the tunnel when not demoing | Owner chose tunnel over deploying for now |
| D-38 | 2026-11-12 | **Project = one hotel.** Signing in lands on a Projects home ("Continue where you left off" = last project opened on this device, else newest; one card per hotel; "List a new hotel"). No hotels yet → straight to a 3-step setup wizard (`/new`). Deleting a project is a **soft delete** (`DELETE /properties/{id}` sets `archived_at`, stops its running agent work, hides its runs); admin/manager only. `python -m app.cli purge-property` hard-deletes (test data only) | KK feedback 2026-11-12; owner chose "1 project = 1 hotel" |
| D-39 | 2026-11-12 | **Markets: United States (default) and India**, picked per project. Country decides currency (USD/INR) and distance unit (miles/km) via `app/core/regions.py`; distances stay stored in km and are converted for display. Address search is limited to the chosen country (Nominatim `countrycodes`). Replaces the hard-coded INR / `IN` / `en-IN` defaults | Owner: "US for now, user can pick US or India" |
| D-40 | 2026-11-12 | **Agent starts automatically** when a project is created (`POST /properties` with `start_agent: true`, on by default in the wizard, can be switched off). First run uses the owner's targeting, OpenStreetMap (+ web search if configured), **max 50 companies, $2 cap** (`AUTOSTART_MAX_COMPANIES`, `AUTOSTART_BUDGET_USD`). Wizard default search distance 5 mi (US) / 8 km (India) | KK: "automatically fill businesses"; low cap because it spends AI quota without a click |
| D-41 | 2026-11-12 | **Plain language everywhere.** Agent step names reworded for hotel owners; a "?" explanation next to scores, tiers, signals, evidence and settings (`src/lib/halo-glossary.ts`); new "How Halo's AI works" page; "Connectors" page (OpenStreetMap, CSV, web search live; Google Places, Apollo, LinkedIn, HubSpot, Salesforce, Gmail/Outlook, calendar, Slack marked **Coming soon**) | KK: "talk more about AI agent features", "add connectors, add coming soon" |
| D-42 | 2026-11-12 | **Remove "Inhabitr" from everything users or websites see**: logo, page metadata, API title, workspace renamed to **Halo**, crawler user-agent `HaloBot`, cookie `halo_session`, CSV export file names. Internal database/role names (`inhabitr_app`, …) and repo names stay (invisible; renaming means rebuilding the DB) | Owner: "Remove it everywhere" |
| D-43 | 2026-11-12 | **Any country** can be chosen per project (widens D-39). US and India stay pinned as quick picks, every other country is searchable. Currency comes from a country→currency table; distances in miles for US, UK, Liberia and Myanmar, km elsewhere; address search limited to the chosen country. Unknown codes are rejected | Owner: "keep it open, user can choose any country" |
| D-44 | 2026-11-12 | **AI rate limits never sink a run.** (1) `LLM_MAX_RPM` paces AI calls per worker (0 = off; 8 set locally for the free Gemini key). (2) Per-minute 429 → wait 60 s and retry; the classify step retries a busy batch once, then sorts that batch by map tags and continues. (3) Per-day quota 429 → circuit breaker: no more AI calls until the quota resets (capped at 6 h); classify, research and signals use their no-AI paths (map tags, website facts, keyword signals) and the run log says so | Owner's run 2026-11-12 failed on the free Gemini tier (20 requests/day for gemini-2.5-flash) |
| D-45 | 2026-11-13 | **Demo-proof failure handling.** Busy/refused upstreams (AI, address search, news) return readable 503s and every error response carries CORS headers, so the app never shows a false "can't reach the server". The Pitch button always yields a draft (fact-based template when the AI is busy or out of allowance). A website that won't respond after one retry counts as "website unavailable", not a failed step. Free news search (GDELT) is tried once per company and pauses for 2 min when rate-limited (logged once per run); news queries use the hotel's own country. One-company "Re-research" jobs no longer count as agent runs. Any localhost port is an allowed origin (record locally without a tunnel). A full run of ~50 companies dropped from ~13 min to under 2 min | Owner: "error free, recording an end-to-end demo" |
| D-46 | 2026-11-13 | **Demo tunnel: Cloudflare quick tunnel in Docker** (`halo-tunnel` container, `--dns 1.1.1.1`, `--add-host host.docker.internal:host-gateway`, API on `0.0.0.0:8000`). localhost.run dropped idle tunnels and rotated domains mid-session; the local router does not resolve `trycloudflare.com`, so the container uses public DNS and the recording browser needs secure DNS (Cloudflare) turned on. The web app ignores a remembered tunnel URL that differs from the current default. Still a stopgap: a fixed domain (named Cloudflare tunnel or ngrok static domain) is the real fix. |
| D-47 | 2026-11-13 | **Halo Lab: the Harness² method, built into Halo** (supersedes P-11; Google's research code is not used: it targets coding agents, needs Linux + Vertex AI and runs unsandboxed). **Harness** = the tunable parts of the agent, saved as numbered *agent versions* (`agent_versions`, workspace-wide): scoring weights/thresholds + extra guidance for the company-sorting (classify) step. Evidence rules, untrusted-content rule, output formats and the research/signal prompts are **locked** — the Lab cannot edit them, so it cannot loosen fact-checking. **Answer key** = team ratings: 👍 good fit / 👎 not a fit on prospects (`lead_feedback`, one current rating per prospect), signal right/wrong flags (`signal_feedback`), CSV upload (company, website, verdict), and dismissals for industry/size/distance. **Loop** (one worker job, kind `lab`, run log reused): Propose (AI editor suggests 3 edits from the misjudged prospects + saved lessons) → Probe (each edit tested on rated prospects; scoring is re-computed locally, sorting re-run only on rated prospects) → Compose (AI merges the best edits) → Reflect (AI saves lessons in `lab_lessons`). Without AI it falls back to a deterministic threshold/weight search. **Gate**: ratings split 70/30 (stable by prospect id); a version becomes a *candidate* only if it beats the live version on the 30% it never saw. A manager/admin approves it; approval re-scores every prospect. Any older version can be re-activated (rollback). Phases: B1 ratings + versions, B2 loop, B3 approval/rollback UI + How-it-works shows the live version and accuracy. | Owner chose: built-in Lab, ratings in app + CSV, B1→B3 |
| D-48 | 2026-11-16 | **Public combined repo `Bharanivelan/halo`** holds both parts with full history: this API repo at the root and the Lovable app (`nearby-hospitality-prospect-scout`) in `web/` (git subtree). Built in a separate local folder `../halo`; `halo-api` and the Lovable repo stay as they are (Lovable must keep owning its repo, D-35). Sync later with `git pull <halo-api>` and `git subtree pull --prefix=web <web repo> main`. Both histories were scanned for keys, passwords and personal data before the first push; only dev placeholders (`.env.example`) are present | Owner: "push the code to this repository". The repo is public, the two source repos are private |
| D-49 | 2026-11-16 | **Bring your own AI provider: Amazon Bedrock and any OpenAI-compatible server**, next to Gemini and OpenAI. `LLM_PROVIDER=bedrock` calls Bedrock's **Converse API** (boto3), one request shape for every chat model Bedrock hosts (Claude, Nova, Llama, Mistral, ...), including the research agent's tool use; OpenAI-style messages/tools are translated in the gateway (`to_converse` / `from_converse`). Credentials: AWS profile/SSO, access keys, a Bedrock API key (`AWS_BEARER_TOKEN_BEDROCK`) or the standard AWS chain (instance/container role). Models differ, so a rejected request is retried once per known gap (forcing a named tool → "any" → none; system prompt folded into the first turn; output limit halved); JSON is requested in the prompt and extracted from fences/chatter (`parse_json_reply`, now used for all providers). `LLM_PROVIDER=openai_compatible` + `OPENAI_COMPATIBLE_BASE_URL` covers OpenRouter, Groq, Together, Azure OpenAI, Ollama, LM Studio, vLLM (falls back to `tool_choice=required` and drops JSON mode if refused). Budget guard, cost log, pacing (D-44) and no-AI fallbacks (D-26) are unchanged for every provider. Defaults: DD-21 | Owner: make Halo usable by people on Bedrock or other AI tools. Tested: unit tests with a stubbed Bedrock client; openai_compatible verified live (JSON + forced tool call) against Gemini's OpenAI endpoint. Bedrock not yet run against a real AWS account |
| D-50 | 2026-11-16 | **Hosting: database on Supabase, API + worker on Railway** (replaces the PC + tunnel set-up of D-37/D-46 for shared use; the tunnel stays for local demos). Supabase is used only as managed Postgres (PostGIS, citext, pg_trgm in its `extensions` schema), **not** its Data API/Auth, so D-34 still holds: the API is the single source of data and logic. `scripts/cloud/supabase_init.sql` creates the non-owner `inhabitr_app` role (RLS applies) and revokes Supabase's `anon`/`authenticated` roles from Halo's tables; the Data API is switched off. Connections go through the **session pooler** (IPv4; the direct host is IPv6-only, the transaction pooler breaks prepared statements); pool size per process is configurable (`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`, 4 + 2 in the cloud). One Docker image (`backend/Dockerfile`): the API runs migrations then serves on `$PORT`; the worker uses start command `python -m app.worker`. Existing local data moved with a data-only dump restored under `session_replication_role = replica` (circular FKs). Rehearsed end to end on a Supabase-like local database before the move. Guide: `docs/DEPLOYMENT.md` | Owner chose Supabase + Railway and moving all current data. Permanent URL; works with the PC off; ~$5/month (Railway) |
| D-51 | 2026-11-19 | **Self-service sign-up** next to email + password sign-in (replaces invite-only for new customers). `/signup` page and `POST /auth/signup` `{full_name, email, password, company?}`: creates a **new workspace** (named after the company, else "<first name>'s workspace"; slug gets a random suffix because RLS hides other workspaces' slugs) with the user as **admin**, then signs in exactly like `/auth/login` (shared `_start_session`). Guards: `SIGNUP_ENABLED` switch (invite-only servers turn it off; the page then hides the link), password ≥ `PASSWORD_MIN_LENGTH` (10) and not the email, duplicate email → 409 "Sign in instead", `SIGNUP_RATE_LIMIT_PER_HOUR` (10) per IP via `login_attempts`. Joining an existing team stays admin-created (`app.cli add-user`); invitations by email come later. Public `GET /auth/options` tells the page what to show and reserves `google_enabled` for **Sign in with Google** (planned). `app.cli bootstrap` and sign-up share `app/core/accounts.create_workspace_with_admin` | Owner: "add the traditional username and password flow, sign in and sign up; later login via Google". Email is the username. No email verification yet (needs an email provider) |
| P-11 | 2026-11-12 | **Proposal: Harness² "agent improvement lab"** (google-research/harness2) as an *offline, dev-time* optimiser of the research agent's prompts and guardrails against a labelled eval set (`data/eval`); winners ship as new prompt versions; agent version + accuracy shown on the How-it-works page. Needs a Google Cloud Vertex AI project, runs as CLI with unrestricted network (dev machine only), research software not officially supported. Not runtime. Shown in the UI as "Coming soon" | Superseded by D-47 (method adopted, code not used) |

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
| DD-21 | Bedrock defaults: region `us-east-1`; models `amazon.nova-lite-v1:0` (fast) / `amazon.nova-pro-v1:0` (standard), Amazon's own models, on demand without a marketplace subscription; unknown models costed at $1 / $4 per 1M tokens; cross-region profile prefixes (`us.`, `eu.`, ...) priced as the base model | B | config `AWS_REGION`, `LLM_DEFAULT_MODELS`, `LLM_PRICING` | D-49 |

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
| A-10 | "Inhabitr" usable as product name | Trademark check | Rename (brand isolated in config/tokens) | Superseded: product is Halo, Inhabitr removed (D-42) |
