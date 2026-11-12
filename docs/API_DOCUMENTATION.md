# Inhabitr — API Documentation (v1)

> Version 1.0 · 2026-11-09 · Design-stage contract. The FastAPI app will publish the authoritative OpenAPI schema at `/api/v1/openapi.json`; this document defines intent and conventions. The Phase 1 mock layer (MSW) implements this contract.

---

## 1. Conventions

| Topic | Convention |
|---|---|
| Base path | `/api/v1` (major version in path; additive changes don't bump it) |
| Format | JSON, `snake_case` fields, ISO-8601 UTC timestamps (`2026-11-09T06:30:00Z`), UUID ids |
| Auth | Session cookie `__Host-inhabitr_session`; mutations require `X-CSRF-Token` |
| Tenancy | Workspace comes from the session (no workspace id in URLs). Property-scoped resources take `property_id` in path or query |
| Pagination | Cursor-based: `?limit=50&cursor=<opaque>` → `{ "items": [...], "next_cursor": "…" \| null, "total_estimate": 1234 }` (limit max 200) |
| Filtering | Query params: `status=qualified,dismissed` (comma = OR), ranges `fit_min=60`, `distance_max_km=10`, search `q=` |
| Sorting | `sort=-priority,name` (minus = descending); allowed fields documented per endpoint |
| Long operations | Always jobs: `202 Accepted` + job resource; poll job URL |
| Idempotency | `Idempotency-Key` header supported on POST endpoints that create jobs/imports |
| Errors | RFC 9457 `application/problem+json` (below) |
| Rate limits | `429` with `Retry-After`; login and job-creation limited |
| Not found vs forbidden | Resources outside a user's access return `404` |

### 1.1 Error format

```json
{
  "type": "https://inhabitr.app/problems/validation-error",
  "title": "Validation failed",
  "status": 422,
  "detail": "radius_km must be between 1 and 50",
  "instance": "/api/v1/discovery/jobs",
  "request_id": "req_01JC…",
  "errors": [{"field": "config.radius_km", "code": "out_of_range", "message": "…"}]
}
```

| `type` suffix | Status |
|---|---|
| `validation-error` | 422 |
| `unauthenticated` | 401 |
| `forbidden` | 403 (only where existence is not secret, e.g. admin endpoints) |
| `not-found` | 404 |
| `conflict` (e.g. invalid status transition) | 409 |
| `budget-exceeded` | 409 |
| `rate-limited` | 429 |
| `provider-unavailable` | 503 |
| `internal-error` | 500 (no internals in body) |

---

## 2. Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | `{email, password}` → sets cookie; returns `Me` |
| POST | `/auth/logout` | revokes session |
| GET | `/auth/me` | current user, workspace, role, accessible properties, `csrf_token` |
| POST | `/auth/invites/accept` | `{token, full_name, password}` → creates user/membership, logs in |
| POST | `/auth/password-reset/complete` | `{token, password}` |
| POST | `/auth/password` | change own password `{current_password, new_password}` |

```json
// GET /auth/me
{"user":{"id":"…","email":"priya@example.com","full_name":"Priya R"},
 "workspace":{"id":"…","name":"Demo Workspace","is_demo":true},
 "role":"rep","properties":[{"id":"…","name":"Hypothetical Upscale Hotel OMR","is_hypothetical":true}],
 "csrf_token":"…"}
```

---

## 3. Admin (Admin role)

| Method | Path | Description |
|---|---|---|
| GET/POST | `/admin/members` | list / invite (`{email, role, property_ids}` → returns invite link in MVP) |
| PATCH | `/admin/members/{membership_id}` | role, active, property access |
| POST | `/admin/members/{membership_id}/password-reset` | returns reset link |
| GET/PUT | `/admin/providers/{provider}` | config (secret write-only; response shows `has_secret: true`) |
| GET/POST | `/admin/scoring-models` | list / create new version |
| POST | `/admin/scoring-models/{id}/activate` | activate version |
| POST | `/properties/{id}/rescore` | job: rescore all accounts with active model |
| GET/PATCH | `/admin/workspace` | settings (default budget, limits, currency, timezone) |
| GET | `/admin/audit-logs` | filters: actor, action, entity, date range |

---

## 4. Properties

| Method | Path | Description |
|---|---|---|
| GET | `/properties` | list accessible projects; each has `country`, `currency`, `distance_unit`, `created_at`, `latest_job` |
| POST | `/properties` | create (Manager+). `country` = `US` (default) or `IN` (D-39). `start_agent: true` also starts the first capped run and returns `started_job_id` (D-40) |
| GET/PATCH | `/properties/{id}` | detail / update |
| DELETE | `/properties/{id}` | delete project (soft: archives, stops running work, hides its runs) → 204 (Manager+, D-38) |
| PUT | `/properties/{id}/offerings` | replace offerings set |
| GET/PUT | `/properties/{id}/target-profile` | default target profile |
| GET/POST/DELETE | `/properties/{id}/competitors[/{cid}]` | free-text competitors |
| GET | `/geocode?q=&country=US` | address → candidates, limited to the country (server-side; cached) |
| GET | `/properties/{id}/overview` | funnel counts, recent signals, my accounts, running jobs |

```json
// POST /properties
{"name":"Hypothetical Upscale Hotel OMR","brand":"Hypothetical",
 "address_line":"Rajiv Gandhi Salai","locality":"Sholinganallur","city":"Chennai","state":"Tamil Nadu",
 "location":{"lat":12.90,"lng":80.23},"lifecycle":"pre_opening","opening_date":"2027-05-01",
 "rooms_count":220,"meeting_rooms_count":6,"largest_meeting_capacity":180,"banquet_capacity":400,
 "restaurants_count":3,"facilities":["pool","gym","business_center"],"is_hypothetical":true}
```

---

## 5. Discovery

| Method | Path | Description |
|---|---|---|
| POST | `/discovery/parse-request` | `{property_id, current_config, text}` → `{patch: [{field, from, to, reason}]}` (no side effects) |
| POST | `/discovery/estimate` | `{config}` → estimate ranges + assumptions |
| POST | `/discovery/jobs` | `{config, nl_request?}` → `202` job |
| GET | `/discovery/jobs?property_id=` | list jobs |
| GET | `/discovery/jobs/{id}` | progress (poll every 2 s while running) |
| GET | `/discovery/jobs/{id}/events?after_id=` | progress messages |
| GET | `/discovery/jobs/{id}/tasks?status=failed` | per-company tasks |
| GET | `/discovery/jobs/{id}/results?outcome=filtered_out` | candidates and outcomes |
| POST | `/discovery/jobs/{id}/cancel` | graceful cancel |
| POST | `/discovery/jobs/{id}/resume` | `{new_budget_usd?}` |
| POST | `/discovery/jobs/{id}/retry-failed` | re-enqueue failed tasks |

```json
// POST /discovery/estimate → 200
{"companies":{"candidates":{"low":60,"expected":110,"high":180},"researched":{"low":30,"expected":50,"high":50}},
 "cost_usd":{"low":2.1,"expected":3.6,"high":6.4},
 "duration_min":{"low":12,"expected":22,"high":40},
 "assumptions":["standard depth","pass rate 0.5 (default, no history)","search: tavily @ configured price"],
 "is_calibrated":false}
```
*(numbers illustrative)*

```json
// POST /discovery/jobs → 202
{"job_id":"0193…","status":"queued","links":{"self":"/api/v1/discovery/jobs/0193…"}}
```

```json
// GET /discovery/jobs/{id} → 200
{"id":"0193…","property_id":"…","status":"running","started_at":"…",
 "budget_usd":5.0,"spent_usd":1.42,
 "stages":[
   {"key":"plan","label":"Understanding request & geography","status":"succeeded"},
   {"key":"discover","label":"Discovering companies","status":"succeeded","counts":{"found":124}},
   {"key":"resolve","label":"Removing duplicates","status":"succeeded","counts":{"merged":17,"companies":107}},
   {"key":"classify","label":"Filtering for relevance","status":"succeeded","counts":{"kept":50,"filtered_out":57}},
   {"key":"research","label":"Researching companies","status":"running","counts":{"pending":21,"running":5,"succeeded":22,"failed":2}},
   {"key":"signals","label":"Identifying business signals","status":"running","counts":{"succeeded":20}},
   {"key":"score","label":"Scoring accounts","status":"running","counts":{"succeeded":19}},
   {"key":"validate","label":"Validating evidence","status":"running","counts":{"downgraded_claims":6}}],
 "new_accounts_cursor":"…","recent_events":[{"id":812,"level":"warning","message":"robots.txt disallows example.com; skipped"}]}
```

---

## 6. Imports

| Method | Path | Description |
|---|---|---|
| POST | `/imports` | multipart upload (`file`, `property_id`) → import with detected columns + preview rows |
| PUT | `/imports/{id}/mapping` | `{mapping: {name: "Company", domain: "Website", …}}` → validation summary |
| POST | `/imports/{id}/commit` | `{mode: "standalone"\|"attach_to_job"}` → `202` |
| GET | `/imports/{id}` | status, counts, row errors |

---

## 7. Companies (evidence)

| Method | Path | Description |
|---|---|---|
| GET | `/companies/{id}` | profile projection + identifiers + locations |
| GET | `/companies/{id}/claims?field=&kind=` | claims with source summaries |
| GET | `/companies/{id}/signals` | signals sorted by recency |
| GET | `/companies/{id}/sources` | sources |
| GET | `/companies/{id}/accounts` | related properties (accounts in other accessible properties) |
| PATCH | `/companies/{id}` | `do_not_contact`, manual corrections (creates `manual` claims) |

```json
// claim item
{"id":"clm_…","field":"hq_location","value":{"city":"Bengaluru","country":"IN"},"kind":"fact",
 "confidence":0.9,"grounding_status":"passed","evidence_quote":"headquartered in Bengaluru with offices in Chennai and Pune",
 "source":{"id":"src_…","url":"https://example.com/about","title":"About us","source_type":"website",
           "retrieved_at":"2026-11-08T10:12:00Z","published_at":null},
 "data_origin":"real"}
```

---

## 8. Accounts

| Method | Path | Description |
|---|---|---|
| GET | `/properties/{pid}/accounts` | explorer list (filters/sort below) |
| GET | `/accounts/{id}` | account detail (company summary, score, top claims, signals, roles, contacts, status) |
| PATCH | `/accounts/{id}` | `status`, `owner_membership_id`, `dismissed_reason`, `dismissed_note` (validated transitions) |
| POST | `/properties/{pid}/accounts/bulk` | `{account_ids, action: "assign"\|"set_status"\|"dismiss", params}` |
| GET | `/accounts/{id}/score` | current score with breakdown + history |
| GET | `/accounts/{id}/roles` | target role recommendations |
| GET | `/properties/{pid}/accounts/export.csv` | same filters as list |
| GET | `/properties/{pid}/accounts/map` | lightweight points for map view |
| GET/POST/PATCH/DELETE | `/saved-views[/{id}]` | saved views |

Filters: `q`, `status`, `tier`, `industry`, `distance_max_km`, `employee_range`, `fit_min`, `intent_min`, `confidence_min`, `signal_type`, `signal_max_age_days`, `owner` (`me`, id, `unassigned`), `actionability`, `data_origin`.
Sort fields: `priority`, `fit`, `intent`, `confidence`, `distance_km`, `name`, `last_activity_at`, `top_signal_age`.

```json
// list item
{"id":"acc_…","company":{"id":"…","name":"Example Analytics Pvt Ltd","domain":"example.com","industry":"it_services",
 "employee_range":"201-500","data_origin":"real"},
 "distance_km":4.2,"tier":"A","priority":68.4,"fit":74,"intent":59,"confidence":63,
 "actionability":"roles_identified",
 "top_signal":{"type":"new_office_or_center","title":"Opens new delivery centre in Perungudi","age_days":41},
 "status":"qualified","owner":{"id":"…","name":"Priya R"},"last_activity_at":"…"}
```

---

## 9. Contacts

| Method | Path | Description |
|---|---|---|
| GET | `/properties/{pid}/contacts` | contacts across the property's accounts |
| GET | `/companies/{id}/contacts` | per company |
| POST | `/companies/{id}/contacts` | create (`full_name`, `title`, `role_code`, `source_note` required) |
| PATCH/DELETE | `/contacts/{id}` | update / archive |
| POST/PATCH/DELETE | `/contacts/{id}/channels[/{chid}]` | email/phone |

---

## 10. Copilot

| Method | Path | Description |
|---|---|---|
| POST | `/accounts/{id}/copilot` | `{offering, contact_id?, role_code?, tone?}` → `202` (short job) or `200` if fast; returns output |
| GET | `/accounts/{id}/copilot` | versions |
| PATCH | `/copilot-outputs/{id}` | save edits |
| POST | `/copilot-outputs/{id}/copied` | logs activity |
| POST | `/copilot-outputs/{id}/mark-sent` | logs `email_sent`, sets account `outreach_sent` |

Errors: `409 do-not-contact`, `422 insufficient-evidence` (fewer than N FACT claims).

---

## 11. Pipeline

| Method | Path | Description |
|---|---|---|
| GET | `/properties/{pid}/opportunities` | board/list; filters: stage, owner, offering |
| POST | `/accounts/{id}/opportunities` | create (sets account `engaged`) |
| PATCH | `/opportunities/{id}` | stage, value, probability, close date, owner; `lost` requires `loss_reason` |
| GET | `/accounts/{id}/activities` | timeline |
| POST | `/accounts/{id}/activities` | note/call/meeting/email_sent |

---

## 12. Activity, usage & eval

| Method | Path | Description |
|---|---|---|
| GET | `/activity/jobs` | all jobs (filters: property, status, date) |
| GET | `/activity/usage?group_by=job\|step\|model&from=&to=` | tokens and cost |
| GET | `/activity/llm-calls?job_id=` | call log (no payloads unless debug capture) |
| POST | `/eval/datasets` | upload ground-truth CSV |
| POST | `/eval/runs` | `{dataset_id, property_id, config}` → job |
| GET | `/eval/runs/{id}` | metrics |

---

## 13. Health

`GET /healthz` (liveness) · `GET /readyz` (DB + migrations) — unauthenticated, no sensitive info.
