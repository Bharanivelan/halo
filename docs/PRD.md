# Inhabitr — Product Requirements Document (MVP)

> Version 1.0 · 2026-11-09 · Status: **Approved scope** (see DECISION_LOG D-01…D-19, P-01…P-08)
> Requirement IDs (`FR-x.y`, `NFR-x`) are referenced from TASK_TRACKER and tests.

---

## 1. Problem, goals, non-goals

**Problem.** Pre-opening hotel sales teams must build a corporate account base quickly with no history, using fragmented manual research. They cannot easily tell which nearby companies have real demand, why, who to approach, or what to say — and they rarely capture why leads fail.

**Goals (MVP)**
- G1. Reduce the time to build a qualified, prioritised account list for one property from weeks to hours.
- G2. Make every recommendation inspectable: sources, quotes, dates, verification status.
- G3. Capture outcomes (dismiss reasons, won/lost, loss reasons) from day one to enable score calibration.
- G4. Provide a polished, enterprise-grade experience usable daily without any chat interface.

**Non-goals (MVP)**
- Replacing a hotel's sales-and-catering system or CRM.
- Sending any communication (email, LinkedIn, SMS) from the platform.
- Consumer (B2C) marketing, Meta Ads.
- Contact data acquisition from paid providers.

---

## 2. Scope

### 2.1 In scope

| Area | MVP capability |
|---|---|
| Platform | Invite-only session auth; workspace; roles Admin / Manager / Rep; property-level access; audit log |
| Properties | Create/edit; map pin + geocoding; capacities; offerings; target profile; radius; pre-opening date; *hypothetical* flag |
| Discovery | Config form (NL request optional → structured config, user confirms); cost estimate + budget cap; CSV / OSM / web search (+ optional Places, off by default); dedup; classification; live progress with partial results; cancel; resume; retry failed |
| Research | Bounded research agent; claims (FACT/INFERENCE/UNKNOWN) with sources and grounding validation; company profile |
| Signals | Dated signals from websites, search and GDELT news; taxonomy; recency decay |
| Scoring | Fit / Intent / Confidence / Actionability; versioned; explainable breakdown linked to evidence |
| Accounts | Explorer: search, filters, sort, pagination, bulk select, assign, dismiss-with-reason, saved views, CSV export, map view; inspector panel; account page |
| Contacts | Recommended target roles; manual contact CRUD; do-not-contact flag |
| Copilot | On-demand brief, recommended offering, email draft, discovery-call questions; editable; versioned; copy + mark sent |
| Pipeline | Account prospecting status; Opportunities (offering, value, close date, probability, loss reason); board; activities & notes |
| Overview | Funnel per property; recent signals; my accounts; running jobs |
| Activity | Jobs, step/task logs, failures, tokens and cost per job and per company |
| Evaluation | Ground-truth dataset format; eval runner + report |
| Demo | Seeded demo workspace with a hypothetical OMR property; mock data badged everywhere |

### 2.2 Out of scope (MVP)

Automated sending and sequences · Meta Ads / B2C · LinkedIn automation · licensed contact providers & email verification · competitor intelligence (beyond a free-text competitor list) · revenue attribution/ROI · CRM sync · SSO · billing · public signup · drive-time isochrones · scheduled re-discovery · cross-workspace company graph · native mobile apps.

---

## 3. Personas

**Priya — Sales Manager (Rep), primary user.** Corporate & MICE sales for a pre-opening property. Lives in tables and email. Needs: "20 accounts worth contacting this week, why, who, and what to say." Skeptical of AI; trusts sources.

**Arjun — Director of Sales / pre-opening lead (Manager).** Owns the account-base target before opening. Configures the property, runs discovery, assigns accounts, reviews pipeline weekly.

**Admin.** Invites users, manages provider keys and budgets, edits scoring model.

*Data model also supports (no dedicated UI in MVP):* Cluster DOS across properties, GM/owner reporting, marketing manager (B2C, future).

---

## 4. User journeys

### J1 — Set up a property (Manager, ~5 min)
1. Properties → New property.
2. Name, brand, address → geocoded pin; drag to correct.
3. Status: pre-opening + opening date.
4. Capacities: rooms, meeting rooms, largest meeting capacity, banquet capacity, restaurants, facilities.
5. Offerings: corporate rate, MICE, long stay, F&B (with relevant details).
6. Target profile: radius (default 15 km), industries, employee range, notes.
7. Save → Property overview with a readiness checklist ("Run your first discovery").

### J2 — Run discovery (Manager)
1. Discovery → New run. Form pre-filled from property target profile.
2. Optional: type a request ("prioritise companies with lots of visiting clients") → system proposes changes to the structured config as a diff; user accepts/edits.
3. Optional: attach a CSV import as an additional source.
4. Choose sources (CSV, OSM, web search; Places if enabled) and max companies.
5. See estimate (company count range, cost range, duration range) and set/confirm budget cap.
6. Start → run screen: stage timeline (pending/running/done/failed + counts), live results table, failures with reasons and retry, cost-so-far vs budget.
7. Completion: summary (found, merged, filtered out and why, researched, scored, failed) → "Review accounts".

### J3 — Triage accounts (Rep, daily)
1. Accounts (property-scoped) sorted by Priority.
2. Each row: company, industry, distance, scale, Fit, Intent, Confidence badge, top signal + age, actionability, status, owner.
3. Keyboard `j/k` moves selection; inspector panel shows score breakdown, key facts with evidence chips, top signals, recommended roles, next action.
4. Actions: qualify, assign, dismiss (reason required), open full page; bulk versions of these.
5. Save current filters/sort/columns as a view.

### J4 — Work an account (Rep)
1. Account page: overview, hospitality opportunity, facts (by kind), signals timeline, sources, score, roles, contacts, activity, related properties.
2. Add a contact manually (name, title, role, business email/phone, source note).
3. "Prepare outreach" → choose contact or role and offering → generate brief + email draft + call questions.
4. Edit; hover any factual sentence to see its claim/source; copy; "Mark as sent" → status `outreach_sent`, activity logged.

### J5 — Pipeline (Rep & Manager)
1. When a prospect responds positively: "Create opportunity" (offering, name, value, expected close, probability).
2. Pipeline board by stage; drag to move; filter by owner/offering.
3. Log notes, calls, meetings as activities.
4. Close as Won or Lost (loss reason required).
5. Overview funnel reflects counts per stage.

---

## 5. Functional requirements and acceptance criteria

### FR-1 Workspace, auth & access
- **FR-1.1** Invite-only: Admin invites by email + role; invite link is single-use and expires (default 72 h).
- **FR-1.2** Login with email + password (Argon2id); session stored server-side; HttpOnly, Secure, SameSite=Lax cookie; idle timeout 7 days, absolute 30 days (configurable).
- **FR-1.3** Roles: **Admin** (everything), **Manager** (all properties; discovery, assignment, pipeline; no user/provider/scoring admin), **Rep** (assigned properties only; accounts, contacts, copilot, pipeline).
- **FR-1.4** Admin-triggered password reset generates a single-use link.
- **FR-1.5** Audit log for: logins (success/failure), invites, role/access changes, provider key changes, scoring model changes, exports, contact deletion, do-not-contact changes.
- *AC:* A Rep requesting another property's account receives 404 (not 403, to avoid leaking existence); verified by API test and an RLS test.

### FR-2 Properties
- **FR-2.1** CRUD with fields in DATABASE_SCHEMA `properties`.
- **FR-2.2** Geocoding via configurable provider (default: OSM Nominatim within its usage policy); manual pin override always possible.
- **FR-2.3** Offerings from fixed taxonomy: `corporate_rate`, `mice`, `long_stay`, `fnb`.
- **FR-2.4** Target profile: radius (1–50 km), industries (taxonomy), employee range, free-text ICP notes.
- **FR-2.5** `is_hypothetical` flag renders a persistent "Hypothetical property" badge.
- *AC:* Radius ring renders on map; changing radius does not alter existing accounts' data but the explorer's "within radius" filter updates.

### FR-3 Discovery
- **FR-3.1** Config = `DiscoveryConfig` (schema in AGENT_ARCHITECTURE §3). Defaults from property.
- **FR-3.2** Optional NL request → structured config proposal shown as diff; nothing runs until user confirms.
- **FR-3.3** Estimate endpoint returns ranges for companies, cost and duration, with the assumptions used.
- **FR-3.4** Budget cap required (default from workspace settings). When the next call would exceed the cap, job → `paused_budget`; user may raise cap and resume, or finish with partial results.
- **FR-3.5** Sources: CSV, OSM, web search, website fetch, GDELT; Google Places only if Admin enabled it with a key.
- **FR-3.6** Dedup within workspace by identifiers (domain, OSM id, Places id) then normalised name + geo proximity; merges recorded in `discovery_results`.
- **FR-3.7** Filtered-out candidates retain a reason (`not_business_office`, `out_of_radius`, `industry_mismatch`, `duplicate`, `insufficient_data`) and are reviewable.
- **FR-3.8** Progress: per-stage status and counts; per-company task status; partial results visible as soon as each account is scored.
- **FR-3.9** Cancel (graceful: running tasks finish, no new tasks start); Resume; Retry failed tasks.
- **FR-3.10** Job ends `completed`, `completed_with_errors`, `failed` (only if the job cannot proceed at all), or `cancelled`.
- *AC:* Killing the worker mid-job and restarting it results in the job continuing without duplicate companies, claims or scores (idempotency test).

### FR-4 CSV import
- **FR-4.1** Upload CSV (≤ 5 MB, ≤ 5,000 rows); column mapping UI (name required; domain, address, city, industry, notes optional).
- **FR-4.2** Row validation with per-row errors; valid rows imported.
- **FR-4.3** Imported companies dedupe against existing; source type `csv_import` with file name, user, time.
- **FR-4.4** Import can be standalone (creates Accounts as `discovered`) or attached to a discovery run (enters the pipeline at Resolve).

### FR-5 Research & evidence
- **FR-5.1** Per company, the research agent produces claims for the controlled field list (AGENT_ARCHITECTURE §5.2).
- **FR-5.2** Every FACT claim must reference a source fetched in the same run and include an evidence quote; the grounding validator checks the quote exists in the source text. Failed → stored as `unknown` with `grounding_status=failed`.
- **FR-5.3** INFERENCE claims must cite ≥1 supporting claim or source and are labelled "Inference" in UI.
- **FR-5.4** Fields with no evidence display "Unknown" — never blank or guessed.
- **FR-5.5** Sources display URL, type, title, published date (if known), retrieval date, licence tag.
- *AC:* No FACT claim exists in the DB with `grounding_status != passed` (DB constraint + test).

### FR-6 Signals
- **FR-6.1** Signal types and default strengths per AGENT_ARCHITECTURE §6.
- **FR-6.2** Each signal: type, title, description, source, `published_at` (or null = undated), discovered_at, confidence, implied offering, recommended approach.
- **FR-6.3** Undated signals and signals older than the window (default 365 days) don't contribute to Intent and display as "Historical".
- *AC:* Recency decay is unit-tested with fixed dates.

### FR-7 Scoring
- **FR-7.1** Axes: Fit (0–100), Intent (0–100), Confidence (0–100), Actionability (`none`/`roles_identified`/`contact_available`). Priority = weighted Fit+Intent → tier A/B/C.
- **FR-7.2** Breakdown per factor: value, weight, contribution, explanation, evidence IDs.
- **FR-7.3** Scoring models versioned; Admin can create a new version; rescoring is an explicit action; each score records its model version.
- **FR-7.4** Scoring is deterministic code; same inputs + same model version → same score.
- *AC:* Property-based test: shuffling claim order does not change scores.

### FR-8 Accounts explorer & account page
- **FR-8.1** Columns: Company, Industry, Distance, Scale, Priority tier, Fit, Intent, Confidence, Top signal (+age), Actionability, Status, Owner, Last activity.
- **FR-8.2** Search (name/domain), filters (status, tier, industry, distance, scale, signal type, signal age, owner, confidence, has contact, data origin), multi-column sort, cursor pagination, column show/hide.
- **FR-8.3** Bulk: assign owner, change status, dismiss (reason), export.
- **FR-8.4** Saved views (personal or shared).
- **FR-8.5** CSV export of current view (respecting source licence tags — fields from sources with non-exportable licences are omitted; none in MVP default sources).
- **FR-8.6** Inspector panel (no navigation) and full account page.
- **FR-8.7** Map view with property pin, radius ring, account markers coloured by tier.
- **FR-8.8** Dismiss reasons: `not_relevant_industry`, `too_small`, `too_far`, `already_customer`, `competitor_relationship`, `bad_data`, `duplicate`, `other` (+note).

### FR-9 Contacts
- **FR-9.1** Recommended target roles per account with rationale (rules by offering and company scale).
- **FR-9.2** Manual contact CRUD; required: name, company; source note required ("met at event", "company website /team page" + URL…).
- **FR-9.3** Business email/phone stored as channels; marked `unverified` unless user marks verified with a note.
- **FR-9.4** Do-not-contact flag on contact or company blocks draft generation for it.

### FR-10 Copilot
- **FR-10.1** User-triggered only, per account.
- **FR-10.2** Outputs: brief (summary, hospitality opportunity, recommended offering, approach), email draft (subject + body), discovery-call questions.
- **FR-10.3** Email drafts may only state facts from FACT claims; INFERENCE allowed only in internal brief, labelled.
- **FR-10.4** Each factual sentence carries claim references; UI shows them on hover; a post-generation validator rejects drafts referencing unknown claim IDs.
- **FR-10.5** Drafts are versioned; edits saved; "Copy" and "Mark as sent" log activities; mark-sent sets account status `outreach_sent`.
- **FR-10.6** Pre-opening framing available (opening date, pre-opening rates) using property data only.

### FR-11 Pipeline
- **FR-11.1** Account prospecting status: `discovered → qualified → contact_identified → outreach_prepared → outreach_sent → engaged | dismissed` (transitions may skip forward; moving backward allowed with activity log).
- **FR-11.2** Opportunity stages: `interested → meeting_scheduled → negotiation → won | lost`.
- **FR-11.3** Creating an Opportunity sets account status `engaged`.
- **FR-11.4** Lost requires loss reason: `price`, `location`, `existing_hotel_contract`, `no_current_need`, `chose_competitor`, `no_response`, `other`.
- **FR-11.5** Activities: note, call, meeting, email_sent (manual), status_change, stage_change, draft_copied, system.

### FR-12 Overview & Activity
- **FR-12.1** Overview: funnel counts per property, new signals (last 30 days), my accounts needing action, running jobs.
- **FR-12.2** Activity: job list, job detail (steps, tasks, errors, retries), LLM/provider usage and cost by job, step, model.

### FR-13 Evaluation
- **FR-13.1** Load ground-truth CSV (data/eval).
- **FR-13.2** Run discovery+research against eval property; compute metrics in §8; store `eval_runs`.

### FR-14 Demo workspace
- **FR-14.1** Seed command creates a demo workspace with a hypothetical upscale OMR property.
- **FR-14.2** Mock records have `data_origin = mock` and display a "Mock" badge; hypothetical property shows a "Hypothetical" badge.
- **FR-14.3** Real discovery runs inside the demo workspace produce `data_origin = real` records, visually distinct from mock.
- **FR-14.4** Mock data never appears outside a workspace flagged `is_demo`.

---

## 6. Non-functional requirements

| ID | Area | Requirement |
|---|---|---|
| NFR-1 | Tenant isolation | Every tenant table has `workspace_id`; app-layer scoping **and** Postgres RLS |
| NFR-2 | Secrets | Env/secret store only; provider keys encrypted at rest (Fernet/AES-GCM with key from env); never sent to frontend |
| NFR-3 | Web security | CSRF protection (SameSite + double-submit token on mutations); strict CORS; security headers; rate limits on login (5/min/IP+email) and job creation |
| NFR-4 | Agent safety | Read-only research tools; untrusted-content delimiting; schema + grounding validation; SSRF protection on fetch; robots.txt honoured; no login/CAPTCHA/paywall bypass |
| NFR-5 | Reliability | Resumable jobs; idempotent steps; retries with exponential backoff + jitter; task leases |
| NFR-6 | Cost control | Estimate before run; hard budget cap per job; per-company caps; all spend logged |
| NFR-7 | Performance | Explorer API p95 < 500 ms at 5,000 accounts/property; UI interactions < 100 ms perceived; 50-company job target 20–30 min (to be measured) |
| NFR-8 | Provenance | Sources store URL, type, retrieval time, content hash, licence tag; claims link to sources |
| NFR-9 | Retention | Fetched page text retained N days (default 90) then nulled; quotes and claims retained |
| NFR-10 | Accessibility | WCAG 2.1 AA contrast; full keyboard use of explorer, board, forms; visible focus; reduced-motion respected |
| NFR-11 | Observability | Structured JSON logs with request_id/job_id/task_id; error tracking (Sentry-compatible); LLM call log |
| NFR-12 | Maintainability | Typed end-to-end (OpenAPI → generated TS client); module boundaries; migration per schema change; docs updated per change; tests in CI |
| NFR-13 | Browser support | Latest Chrome, Edge, Firefox, Safari; layouts usable from 1280 px; responsive down to tablet; read-only usable on mobile |
| NFR-14 | Localisation | Currency INR default (configurable per workspace); dates in workspace timezone (default Asia/Kolkata); Indian number formatting option |

---

## 7. UX requirements

- **UX-1 Identity.** Premium enterprise SaaS, calm and dense (inspired by Linear/Attio, not copied), with a distinct Inhabitr identity: warm neutrals, one accent, strong typography, tabular numerals.
- **UX-2 Navigation.** Property switcher at top; main nav: Overview, Accounts, Discovery, Contacts, Pipeline; system nav: Properties, Activity, Settings. No standalone chat.
- **UX-3 Evidence chips.** FACT / INFERENCE / UNKNOWN with distinct, accessible styles (not colour alone); hover popover: quote, source title, URL, retrieved/published dates.
- **UX-4 Score breakdown.** Segmented bars per axis; clicking a segment reveals contributing evidence.
- **UX-5 Freshness.** Signal age shown relatively ("23 d ago") with visual decay; historical signals muted.
- **UX-6 Run timeline.** Stage list with states and counts, live results, failures with reasons and retry; cost-vs-budget meter. Never a bare spinner.
- **UX-7 Explorer.** Split view (table + inspector), keyboard navigation, command palette (⌘/Ctrl+K), comfortable/compact density.
- **UX-8 States.** Every screen designs loading (skeletons), empty (guidance + primary action), partial, error (what happened + what to do) states.
- **UX-9 Data origin.** Mock and hypothetical badges are always visible where such data appears.
- **UX-10 Restraint.** No decorative gradients, giant cards, gratuitous animation or AI sparkle branding. Motion ≤ 200 ms, purposeful.

---

## 8. Success metrics

### 8.1 Evaluation metrics (against ground-truth set; targets are hypotheses, fixed after first run)

| Metric | Definition | Initial target |
|---|---|---|
| Discovery precision | % discovered companies that are real, operating within radius, in target industries | ≥ 70% |
| Discovery recall | % of ground-truth relevant companies found | measure → set |
| FACT accuracy | % FACT claims a human confirms correct | ≥ 90% |
| Grounding pass rate (stored FACTs) | enforced | 100% |
| Signal date accuracy | % signals with correct publish date | ≥ 90% |
| Ranking agreement | overlap of system top-20 vs expert top-20 | measure → set |
| Cost per researched company | job cost ÷ companies researched | measure → set |
| Task failure rate | failed ÷ total tasks | < 5% |

### 8.2 Product metrics (once real users exist)
Accounts reviewed per rep-hour; % accounts qualified vs dismissed (by reason); outreach marked sent; opportunities created; won value; time from discovery to first outreach.

---

## 9. Assumptions & risks

Assumptions A-01…A-10 are tracked in [DECISION_LOG.md](DECISION_LOG.md#assumptions-register). Engineering risks and mitigations: [SYSTEM_ARCHITECTURE.md §14](SYSTEM_ARCHITECTURE.md#14-risks-and-mitigations).
