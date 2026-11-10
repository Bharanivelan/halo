# Halo — Lovable prompt sequence

Use these **in order**, one prompt per message. Wait for each build to finish and check the preview before sending the
next. If Lovable drifts, reply: *"Follow the Project Knowledge rules: data only via src/lib/halo-api.ts, no Supabase."*

---

## Prompt 1 — Foundation, design system, shell, login

> Build the foundation for **Halo**, a premium AI go-to-market command center for multi-location hotel and restaurant
> groups. Follow the Project Knowledge exactly (brand, colour tokens, typography, rules). **Do not add Supabase or any
> backend** — a separate Halo API already exists and will be wired in the next step.
>
> 1. Set up the design system: Tailwind theme + CSS variables for every colour token in dark and light themes (dark is
>    default), fonts (Plus Jakarta Sans, Inter, JetBrains Mono via Google Fonts), radius 16px, and a theme toggle
>    saved in localStorage.
> 2. Create reusable components: `Logo` (glowing gold→teal ring + "halo" wordmark + "by Inhabitr"), `HaloRings`
>    (animated concentric rings, used as decoration), `ScoreRing` (0–100 circular gauge with mono number, colour prop),
>    `TierBadge` (A Hot / B Warm / C Cool), `SignalChip` (coral dot + label + age), `KpiTile` (label, big count-up
>    number, small delta/subtext), `AgentPulse` (violet pulsing dot), `EmptyState` (halo rings illustration + title +
>    text + action), skeleton loaders.
> 3. App shell: collapsible left sidebar (logo, location switcher placeholder, nav: Command center, Agent runs,
>    Prospects, Pipeline; bottom: Settings, theme toggle, user menu) and a top bar (breadcrumbs, search input,
>    gradient **Run agent** button). Routes from the Project Knowledge, each with a placeholder page for now.
> 4. **Login page** (`/login`), the CEO's first impression: split screen. Left: large animated dark map-like canvas
>    with three glowing halo rings pulsing at different positions (Chennai, Coimbatore, Vellore feel), faint dots
>    lighting up inside them, and the headline "Every location has a halo. Halo finds who's inside it." with a one-line
>    subtext "AI agent that discovers, researches and scores the companies around each of your properties."
>    Right: a clean card with email, password, "Sign in" (gradient), and a small "Connection settings" link that opens
>    a dialog with a "Server URL" field (we'll wire it next).
>
> Make it feel premium and alive: subtle motion, depth, crisp typography. Mobile-friendly.

---

## ⏸ Between prompt 1 and 2 — connect GitHub, add the API kit

1. In Lovable: **GitHub → Connect** → create the repository (name it `halo-web`).
2. Tell Claude the repo URL. Claude pushes `src/lib/halo-api.ts` and `src/lib/halo-types.ts` into it
   (Lovable picks them up automatically).
   *Alternative:* paste each file into Lovable with "Create this file exactly as given: …".
3. Start the backend tunnel (`scripts/tunnel.ps1`) and copy the `https://….trycloudflare.com` URL.

---

## Prompt 2 — Wire auth + connection settings

> `src/lib/halo-api.ts` and `src/lib/halo-types.ts` now exist. Never modify them. Wire the app to them:
> - Login form calls `halo.login(email, password)`; on success go to `/`. Show `ApiError.detail || title` inline on
>   failure. Show a spinner on the button while pending.
> - "Connection settings" dialog: input bound to `getApiUrl()` / `setApiUrl()`, a **Test connection** button that calls
>   `halo.health()` and shows: connected ✓, AI provider (`llm_provider`) and whether AI is on (`llm_configured`). Also
>   reachable from Settings.
> - Route guard: if `!halo.isSignedIn()` redirect to `/login`. Listen for the `halo:signed-out` window event and redirect.
> - Load `halo.me()` (user, workspace, role, properties) and `halo.reference()` once via TanStack Query and expose them in
>   a context. User menu shows name, email, role and **Sign out** (`halo.logout()`).
> - Sidebar location switcher lists `me.properties` (name + city); selecting one navigates to `/p/:id`.
> - Global amber banner when `reference.llm_configured` is false (see Project Knowledge rule 8).

---

## Prompt 3 — Portfolio (all locations)

> Build `/` **Portfolio**. Data: `halo.properties()`.
> - Hero: greeting "Good morning, {first name}" + one line: "{n} locations · {total prospects} prospects in their halos".
> - Big MapLibre map (see Project Knowledge) fitted to all locations: gold pin per location with animated halo rings
>   scaled to `radius_km`. Hover → glass tooltip (name, city, prospects). Click → `/p/:id`.
> - Below: responsive grid of **location cards**: name, brand, locality/city, lifecycle badge ("Pre-opening · opens
>   {opening_date}" or "Operating"), radius, prospect count (count-up), and a mini halo ring graphic. Card actions:
>   "Open command center", "Run agent".
> - **Add location** button → sheet with: name, brand, lifecycle, opening date, address search using
>   `halo.geocode(q)` (debounced 400ms, results list → sets lat/lng + locality/city/state/postal_code/country), a small
>   map preview with a draggable pin and a radius slider (1–50 km, default 15) showing the halo live, rooms count,
>   meeting rooms, largest meeting capacity, offerings multi-select (from `reference.offerings`), target industries
>   multi-select (`reference.industries`). Submit `halo.createProperty(input)` (shape: `PropertyInput`, `target:
>   {radius_km, industries, employee_min:null, employee_max:null, notes:null}`, `location:{lat,lng}`, `facilities: []`,
>   `is_hypothetical:false`, `country` default "IN"). Then navigate to the new location.
> - Empty state: halo illustration + "Add your first location to light up its halo."

---

## Prompt 4 — Location command center

> Build `/p/:propertyId` **Command center**. Data: `halo.overview(propertyId)` and `halo.accountsMap(propertyId)`.
> - Header: location name, city, lifecycle badge, radius; actions: **Run agent** (gradient) and "View prospects".
> - KPI row (count-up `KpiTile`s): Prospects (`account_count`), Hot (Tier A), Warm (Tier B), Open pipeline value
>   (`opportunities.open_value` in `currency`), AI spend 30d (`usage_30d.cost_usd`).
> - Left 2/3: **Halo map** — location pin with rings at the radius; prospects as dots coloured by tier (A pulses);
>   click a dot → small glass card (name, tier, status) with "Open dossier". Legend + "Show tiers" toggles.
> - Right 1/3: **Needs attention** (`attention`): company name, tier badge, top signal chip, next step text, link.
>   Then **Fresh signals** (`recent_signals`): signal chip, title, company, age, link to the account.
> - Below: **Funnel** (`funnel`) as a horizontal stepped bar: Discovered → Qualified → Contact identified → Outreach
>   prepared → Outreach sent → Engaged, with counts. **Tier split** donut (recharts) for A/B/C.
> - If `running_jobs` is non-empty: a violet "Agent is working" strip at the top with progress bar and "Watch live".
> - Empty (0 prospects): big halo empty state "Your halo is dark. Run the agent to discover who's around {name}."

---

## Prompt 5 — Launch the agent

> Build `/p/:propertyId/agent/new` **Run the agent**. It configures a `DiscoveryConfig`.
> - Top: a large "Tell the agent what you're looking for" textarea (e.g. "IT and pharma companies with 200+ staff,
>   focus on long stays"). Button **Interpret** → `halo.parseRequest(propertyId, text, currentConfig)`; show each
>   `patch` item as a diff chip ("Radius 15 → 10 km — because …") and apply `config`. If it returns 409, show "AI is
>   off — set the options below manually".
> - Form (defaults from the location: radius from `property.target.radius_km`, industries from target): radius slider
>   (1–50 km) with live halo preview, industries multi-select, employee min/max, offerings focus chips, sources checkboxes from
>   `reference.providers` (disabled with `reason` if not enabled), max companies (1–200, default 50), research depth
>   segmented control (Light / Standard), signal window (90 / 180 / 365 / 730 days, default 365), budget cap USD (default 5, max 500), notes (max 500 chars).
> - Right panel **Estimate** (debounced 600ms → `halo.estimate(config)`): candidates, researched, cost range, duration
>   range as low–expected–high bars, `assumptions` and `warnings` lists.
> - Footer CTA **Launch agent** (gradient) → `halo.startRun(config)` → navigate to `/p/:propertyId/agent/:job_id`.
>   Fields: `property_id`, `csv_import_id: null`, `prioritisation_notes` from notes, `budget_usd`.

---

## Prompt 6 — Live agent run (the wow screen)

> Build `/p/:propertyId/agent/:jobId` **Agent run**. Poll `halo.run(jobId)` every 2s while active.
> This is the showpiece: make it feel like watching an intelligent agent work.
> - Header: status pill (violet pulsing when running, teal completed, amber paused, red failed), started time,
>   duration, who started it. Actions by state: Cancel (running/queued), Resume with new budget (paused_budget →
>   `halo.resumeRun(id, budget)`), Retry failed (`counts.failed > 0` and not active → `halo.retryFailed`).
> - **Stage pipeline**: 7 connected nodes (stages[].label) left→right; done = teal check, running = violet shimmer +
>   pulse, failed = red; under each node `detail` text and a tiny count.
> - **Live counters** (count-up): Found, Companies, Researched, Scored, Failed (`counts`).
> - **Agent thinking feed**: `events` as a terminal-style monospace log on a dark violet-tinted panel, newest at bottom,
>   lines slide in, warnings amber, errors red, auto-scroll with "pause scroll" toggle.
> - **Budget meter**: spent vs reserved vs cap (`spent_usd`, `reserved_usd`, `budget_usd`) as a segmented bar.
> - **Prospects appearing**: list of accounts from `halo.accounts(propertyId, {job_id: jobId, sort: "-priority"})`
>   refreshed every 5s while active — each new row animates in with its tier badge, score rings, top signal.
> - When finished: celebratory but tasteful summary card: "{scored} prospects scored · {A} hot · {B} warm" with buttons
>   "Open prospects" and "Back to command center". Banners for paused / failed / partial failures per state.
> - Run settings in a collapsible "Settings used" panel.
> Also build `/p/:propertyId/agent` (sidebar "Agent runs"): list of `halo.runs(propertyId)` with status, progress,
> counts, cost, started; click → run.

---

## Prompt 7 — Prospects (table + map)

> Build `/p/:propertyId/accounts` **Prospects**. Data: `halo.accounts(propertyId, filters)` (cursor pagination via
> `next_cursor`, `total`).
> - Toolbar: search (`q`), tier filter chips (A/B/C), status select (`reference.account_statuses`), industry select,
>   max distance slider, "Has signal" toggle, sort select (Priority, Fit, Intent, Confidence, Distance, Name, Recent).
>   Filters live in the URL query string. Toggle **Table / Map**.
> - Table (TanStack Table, sticky header, row hover glow): checkbox, Company (name + industry label + locality),
>   Tier badge, Priority (mono), Fit/Intent/Confidence as small inline bars, Top signal chip, Distance, Status, Owner.
>   Row click → dossier.
> - Bulk bar when rows selected: Assign owner (`halo.members()`), Set status, Dismiss (reason from
>   `reference.dismiss_reasons`) → `halo.bulk(...)`; **Export CSV** → `halo.downloadAccountsCsv(propertyId, {ids})`.
>   Toolbar also has "Export all (filtered)".
> - Map view: same filters, dots by tier around the location's halo; side list synced with the map.

---

## Prompt 8 — Account dossier (whom, how, when, what to pitch)

> Build `/p/:propertyId/accounts/:accountId` **Prospect dossier**. Data: `halo.account(id)` (`AccountDetail`).
> Layout: header + 2 columns.
> - **Header**: company name, domain link, industry, size, locality, distance; Tier badge large; three `ScoreRing`s
>   (Fit gold, Intent coral, Confidence teal) + Priority number; status select (`halo.updateAccount`), owner select,
>   "Re-research" (`halo.reResearch`, violet).
> - **Next best action** card (top, gradient border): `next_action.title` + `detail` + a primary button matching
>   `next_action.kind` (add_contact → open contact form; prepare_outreach → scroll to Pitch; create_opportunity → open
>   form; research → re-research).
> - Left column:
>   - **Why now** — `signals`: SignalChip, title, description, `recommended_approach` (as "How to use this"),
>     evidence quote in a quote block, source domain link, age. Historical signals dimmed.
>   - **What we know** — `claims` grouped by `field_label`: value, kind badge (Fact ✓ / Inferred / Unknown), confidence
>     bar, expandable evidence quote + source link. Facts show a small "verified quote" shield.
>   - **Score breakdown** — Fit factors (label, points/weight bar, explanation), Intent signal contributions, Confidence
>     components (coverage, diversity, freshness), and "Missing" items as hints.
> - Right column:
>   - **Who to contact** — `roles` ranked: role label, offering it maps to, rationale. Under it, `contacts` (name,
>     title, email/phone with copy buttons, verification badge, do-not-contact flag) + **Add contact** form
>     (`halo.addContact(company.id, {...source_note required})`).
>   - **Pitch** — offering select (default from top role's offering), tone (Warm/Formal), optional contact →
>     **Generate pitch** (`halo.generatePitch`, show a violet "Agent is writing…" state, can take 40s). Render
>     `content.brief` (summary, opportunity, approach), editable email subject + body (body = `body_blocks` text joined
>     by blank lines; blocks with `claims` show a tiny citation marker that highlights the claim on hover; inference
>     blocks italic), `call_questions` list. Buttons: Save edits (`editPitch`), Copy (`pitchCopied` + clipboard),
>     Mark as sent (`pitchSent`). Version history from `halo.pitches(id)`. Footer note: "Halo drafts. You send."
>   - **Pipeline** — `opportunities` + Create opportunity form (name, offering, value ₹, expected close, probability).
>   - **Timeline** — `activities` with icons by type + quick add (note/call/meeting/email_sent).
>   - **Also near your other locations** — `related_accounts`.

---

## Prompt 9 — Pipeline board + Settings

> 1. `/p/:propertyId/pipeline`: Kanban with columns Interested, Meeting scheduled, Negotiation, Won, Lost from
>    `halo.opportunities(propertyId)`. Cards: company, opportunity name, offering, value (₹, Indian grouping),
>    probability, owner, expected close. Drag between columns → `halo.updateOpportunity(id, {stage})`; moving to Lost
>    opens a dialog requiring `loss_reason` (`reference.loss_reasons`). Column totals at top; total open value hero.
> 2. `/settings`: tabs **Connection** (server URL + test, AI provider/status), **AI usage** (`halo.usage('step')` and
>    `('model')` as bar charts + table: calls, tokens, cost), **Team** (`halo.members()`), **Appearance** (theme).

---

## Prompt 10 — Polish pass

> Do a polish pass across the whole app for a CEO demo: consistent spacing (8px grid), aligned numbers (tabular mono),
> skeletons everywhere, empty and error states per Project Knowledge, keyboard focus, responsive down to 375px, smooth
> page transitions, no layout shift while polling, document titles per page ("Prospects · {location} · Halo"), favicon
> from the Logo ring. Remove any leftover placeholder or lorem text. Check dark and light themes for contrast.
