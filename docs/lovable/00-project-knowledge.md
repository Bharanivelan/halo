# Halo — Project Knowledge (paste into Lovable → Project settings → Knowledge)

## What Halo is
Halo (by Inhabitr) is an AI go-to-market agent for multi-location hospitality businesses (hotel groups, restaurant chains).
The owner pins each location on a map. For any location, Halo's agent discovers the companies around it, researches
each one, detects buying signals (hiring, expansion, new offices, events), scores how good a prospect it is, recommends
whom to approach and how, and drafts an evidence-backed pitch. Humans review and send — Halo never sends anything itself.

Audience: hotel/restaurant owners, sales managers and reps. The CEO demo matters: it must look premium and feel alive.

## Hard rules (always follow)
1. **No Supabase, no Lovable Cloud, no backend code, no mock database.** All data comes from the existing Halo API.
2. **Only call the API through `src/lib/halo-api.ts`** (the `halo` object). Types live in `src/lib/halo-types.ts`.
   Never edit those two files; never invent endpoints or fields that aren't in them.
3. Use TanStack Query for every API call (query keys like `["accounts", propertyId, filters]`). Poll
   `halo.run(id)` every 2 s while status is `queued | running | cancelling`.
4. Auth: if `halo.isSignedIn()` is false → `/login`. Listen for the `halo:signed-out` window event → go to `/login`.
5. Every screen needs loading skeletons, an empty state with a clear next step, and an error state showing
   `ApiError.title` / `detail` with a Retry button. `ApiError.status === 0` means the server URL is wrong or offline:
   show a "Connection settings" button that opens the server-URL dialog.
6. Never fabricate data in the UI. If a field is null, show "Unknown" / "—" in muted text, not a made-up value.
7. Respect evidence: a `Claim` of kind `fact` shows its `evidence_quote` and source link; `inference` is labelled
   "Inferred"; `unknown` is labelled "Unknown". Signals show their source and age.
8. If `reference.llm_configured` is false, show a slim amber banner: "AI research is off — results use map data and
   rules only." (Don't block the UI.)
9. Currency: costs are USD (`$0.42`); opportunity values use the opportunity's `currency` (usually INR → `₹4,50,000`
   Indian grouping). Distances in km with one decimal.
10. Accessibility: visible focus rings, 4.5:1 contrast, keyboard-navigable tables and dialogs, `prefers-reduced-motion`
    disables non-essential animation.

## Brand & visual identity
- **Name:** Halo. Wordmark: "halo" lowercase in Plus Jakarta Sans 700, with a small glowing ring (◯ with gold→teal
  gradient stroke) as the logo mark. Sub-label "by Inhabitr" in small muted text.
- **Concept:** every location radiates a *halo* — concentric glowing rings marking its catchment. Prospects light up
  inside the rings. Use this motif in the logo, map, empty states, loaders and the login screen.
- **Theme:** dark-first "command center" (default), with a polished light theme toggle.

### Colour tokens (define as CSS variables / Tailwind theme; use tokens, never raw hex in components)
| Token | Dark | Light | Use |
|---|---|---|---|
| background | `#070B18` | `#F7F8FC` | app background |
| surface | `#0E1426` | `#FFFFFF` | cards |
| surface-2 | `#151D36` | `#F1F3F9` | raised / hover |
| border | `rgba(255,255,255,0.08)` | `#E3E7F0` | hairlines |
| text | `#E8ECF8` | `#0F172A` | primary text |
| text-muted | `#8A94B3` | `#5B6785` | secondary |
| halo-gold (primary) | `#F6B73C` | `#C98A0B` | primary actions, Tier A, logo |
| aurora-teal | `#2DD4BF` | `#0F9F8F` | Tier B, success, live |
| agent-violet | `#8B5CF6` | `#6D3FE0` | anything the AI agent is doing |
| signal-coral | `#FB7185` | `#E11D48` | buying signals, alerts |
| tier-c slate | `#64748B` | `#64748B` | Tier C, neutral |

Signature gradient: `linear-gradient(135deg, #F6B73C 0%, #FB7185 50%, #8B5CF6 100%)` — use sparingly (logo ring,
primary CTA "Run agent", hero numbers). Background may have a very subtle radial glow (gold at 6% opacity) top-left.

### Typography
- Headings: **Plus Jakarta Sans** (600/700). Body/UI: **Inter** (400/500/600). Numbers, scores, agent log:
  **JetBrains Mono** (tabular figures).
- Scale: 32 / 24 / 18 / 15 / 13 / 12. Generous line-height; never more than 2 weights in one card.

### Components & motion
- shadcn/ui + Tailwind + lucide-react icons + framer-motion + recharts.
- Cards: 16px radius, 1px border token, subtle inner glow on hover; glass effect (backdrop-blur, 70% surface) only for
  floating panels over the map.
- **Score ring**: circular gauge 0–100 (Fit gold, Intent coral, Confidence teal) with the number in mono in the centre.
- **Tier badge**: A = gold glow pill, B = teal, C = slate. Always show letter + label ("A · Hot").
- **Signal chip**: coral dot + type label + age ("Hiring · 6d").
- **Agent activity**: violet accent, a pulsing dot, monospace log lines that slide in, a shimmer on the active stage.
- Numbers count up on first render (KPI tiles). Page transitions: 150ms fade/slide. Respect reduced motion.
- Maps: **MapLibre GL** via `react-map-gl/maplibre` with the free CARTO style
  (dark: `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json`,
  light: `https://basemaps.cartocdn.com/gl/positron-gl-style/style.json`). No Mapbox token. Property = gold pin with
  animated concentric halo rings sized to the radius (km); accounts = dots coloured by tier; Tier A dots softly pulse.

## Information architecture (routes)
- `/login`
- `/` Portfolio — all locations
- `/p/:propertyId` Command center for one location
- `/p/:propertyId/agent/new` Launch the agent (configure a run)
- `/p/:propertyId/agent/:jobId` Live agent run
- `/p/:propertyId/accounts` Prospects table (+ map toggle)
- `/p/:propertyId/accounts/:accountId` Account dossier
- `/p/:propertyId/pipeline` Pipeline board
- `/settings` Connection, AI usage, team

Layout: left sidebar (logo, location switcher, nav: Command center, Agent runs, Prospects, Pipeline; bottom: Settings,
theme toggle, user menu) + top bar (breadcrumbs, global search box for accounts, "Run agent" gradient button).

## Vocabulary (UI copy)
- Property → "Location". Discovery job → "Agent run". Account → "Prospect". Copilot → "Pitch".
- Scores: **Fit** (how well they match what this location sells), **Intent** (recent buying signals),
  **Confidence** (how much evidence we have), **Priority** (overall). Tier A/B/C = Hot / Warm / Cool.
- Offerings: corporate_rate "Corporate stays", mice "Meetings & events", long_stay "Long stays", fnb "Food & beverage".
- Stage keys for runs: plan "Planning", discover "Finding companies", resolve "De-duplicating", classify
  "Classifying", research "Researching", signals "Reading signals", score "Scoring".
- Tone: confident, plain English, short. No exclamation marks. Explain *why* (evidence) next to every recommendation.
