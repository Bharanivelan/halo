# Inhabitr — Design System

> **Status: Proposal v0.1, awaiting owner review** (Phase 1, T-1.2).
> Visual preview (live tokens, components, Overview and Accounts screens): https://claude.ai/artifact/6ssYqwLR4fnYbXM8NmnaEC (private; owner access).
> Once approved, values in this file are implemented in `frontend/src/design/tokens.css` and this document becomes the reference. Changes to tokens are logged in DECISION_LOG.

---

## 1. Identity & philosophy

**Thesis:** Account intelligence for hotel sales, with the evidence attached.

The product should feel like a well-run sales office: calm, exact, quietly confident. Dense where people work (tables, panels), generous where they decide (scores, evidence, next actions).

| Principle | Means in practice |
|---|---|
| Evidence before opinion | Fact / Inference / Unknown marks are the most important visual element. Every claim shows how we know it |
| Calm density | Hairline borders instead of boxes and shadows; 13px UI text; tabular numerals; whitespace groups, never decorates |
| Colour carries meaning | Lagoon = brand + Fit. Marigold = Intent + time. Iris = Inference only. Ink = confidence/meta. Semantic colours = outcomes. Nothing is coloured for decoration |
| Show the work | Long jobs show stages, counts, failures and spend while running. Never a bare spinner |
| Warm, not decorative | Serif only for page titles, company names in headers and quoted evidence |

**Avoid:** gradients, glow/sparkle "AI" styling, chat-first UI, giant KPI cards, traffic-light scores, decorative illustration, shadows on static surfaces.

**Mark (working):** property dot inside a solid radius ring and a dashed discovery boundary, with one marigold point for a company showing a signal. Pending name clearance (A-10).

---

## 2. Colour tokens

Neutrals ("linen") lean slightly toward the accent hue. Dark theme is designed separately: accents get lighter, nothing is simply inverted.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--canvas` | `#F6F7F5` | `#0E1211` | App background |
| `--surface` | `#FFFFFF` | `#141917` | Panels, tables, inputs |
| `--surface-2` | `#F1F3F0` | `#1A201E` | Table headers, sidebar, subtle fills |
| `--surface-3` | `#E7EBE6` | `#222926` | Tracks, pressed states, neutral badges |
| `--border` | `#E0E4DF` | `#252D2A` | Hairlines |
| `--border-strong` | `#C7CEC8` | `#36403C` | Input and button borders |
| `--ink` | `#141917` | `#E7ECE9` | Primary text |
| `--ink-2` | `#4A534F` | `#AAB4AF` | Secondary text |
| `--ink-3` | `#67706B` | `#7F8984` | Tertiary text, meta (≥ 4.5:1) |
| `--ink-4` | `#A3ABA6` | `#56605B` | Placeholder, disabled, decorative only (not for essential text) |
| `--accent` | `#0F6A62` | `#3FB3A4` | Primary actions, selection, focus |
| `--accent-hover` | `#0C554F` | `#5CC4B6` | |
| `--accent-fg` | `#FFFFFF` | `#04201D` | Text on accent fill |
| `--accent-soft` / `--accent-text` / `--accent-line` | `#E3F2EF` / `#0C554F` / `#A6D6CD` | `#12302C` / `#7FD3C6` / `#1F5A52` | Selected rows, Tier B, Fact marks |
| `--fit-1…4` | `#0C554F` `#1A7F74` `#4FA597` `#8CC9BE` | `#8FDCCF` `#4FB8AA` `#2E8A7F` `#1F5F57` | Fit factor segments (strongest → weakest) |
| `--intent` / `-soft` / `-text` / `-line` | `#C88C10` / `#FCF1D8` / `#8A600A` / `#F0CF85` | `#E2A93B` / `#2E2410` / `#EDBE5E` / `#6B5220` | Intent, signals, freshness, budget warnings, new rows |
| `--inference` / `-soft` / `-text` | `#7357C2` / `#F1EDFA` / `#553E9C` | `#9D86E6` / `#231D38` / `#B9A8EF` | AI inference only |
| `--success` / `-soft` / `-text` | `#2F8A55` / `#E7F4EC` / `#24653D` | `#4FB57A` / `#132A1C` / `#74CB97` | Won, engaged, succeeded |
| `--danger` / `-soft` / `-text` | `#C23B2A` / `#FBECE9` / `#A3301F` | `#E5685A` / `#3A1915` / `#F2928A` | Failed, lost, destructive |
| `--info` / `-soft` / `-text` | `#2F5C99` / `#E9EFF8` / `#2A5189` | `#6E9BE0` / `#15223A` / `#9DBDF0` | Neutral notices |
| `--row-hover` / `--row-selected` | `#F3F5F2` / `#EAF5F2` | `#181E1C` / `#12302C` | Table rows |

**Rules**
- Scores are never red/amber/green. Tiers use one lagoon ramp (A solid, B soft, C neutral).
- Iris is reserved for inference so it stays recognisable.
- Semantic colours describe outcomes (won/failed), never quality judgements on accounts.
- State is always encoded in shape or text as well as colour (evidence glyphs, status pips, labels).
- Contrast targets: WCAG 2.1 AA for all text; verified with a checker when tokens are implemented.

---

## 3. Typography

| Role | Family | Fallback | Use |
|---|---|---|---|
| Display | **Newsreader** (400–600, optical size) | Iowan Old Style, Georgia, serif | Page titles, account names in headers, quoted evidence, large empty states |
| Interface | **IBM Plex Sans** (400, 500, 600) | system-ui, Segoe UI, Roboto, sans-serif | Everything else |
| Data | **IBM Plex Mono** (400, 500) | ui-monospace, Consolas, monospace | Domains, IDs, logs, run costs |

Fonts self-hosted in the app (woff2, `font-display: swap`) — no runtime dependency on Google Fonts.

| Token | Size / line | Weight | Family | Use |
|---|---|---|---|---|
| `display-lg` | 44 / 48 | 400 | Display | Onboarding, large empty states |
| `display-md` | 32 / 38 | 400 | Display | Account page header |
| `display-sm` | 24 / 30 | 500 | Display | Page titles |
| `title` | 20 / 28 | 600 | UI | Panel and dialog titles |
| `heading` | 16 / 24 | 600 | UI | Section headings |
| `body-md` | 14 / 22 | 400 | UI | Reading text, inputs |
| `body` | 13 / 20 | 400/500 | UI | **Default UI text**, table cells |
| `small` | 12 / 16 | 400 | UI | Meta, hints, captions |
| `label` | 11 / 14 | 600, caps, +0.06em | UI | Column headers, group labels |
| `kpi` | 28 / 32 | 500 | UI | Overview numbers |

All numeric UI uses `font-variant-numeric: tabular-nums`. Indian digit grouping via workspace locale (DD-15).

---

## 4. Space, size, radius, elevation, motion

**Spacing (4px base):** `--s-0-5` 2 · `--s-1` 4 · `--s-1-5` 6 · `--s-2` 8 · `--s-3` 12 · `--s-4` 16 · `--s-5` 20 · `--s-6` 24 · `--s-8` 32 · `--s-10` 40 · `--s-12` 48 · `--s-16` 64.

**Sizes:** controls 28 / 32 / 40 (32 default) · table rows 40 comfortable / 32 compact · top bar 48 · sidebar 232 (56 collapsed) · inspector 400 (resizable 360–560) · content max 1440 · forms max 720 · icons 16 (14 in chips), Lucide, stroke 1.75.

**Radius:** `--r-xs` 3 (chips, tags) · `--r-sm` 5 (buttons, inputs) · `--r-md` 8 (panels, menus, tables) · `--r-lg` 12 (dialogs, drawers) · `--r-pill` (filter chips, avatars).

**Elevation:** Level 0 = hairline only (all page surfaces) · Level 1 `--shadow-1` (menus, popovers, tooltips) · Level 2 `--shadow-2` (dialogs, drawers, command palette, toasts). Dark theme uses deeper shadows plus borders.

**Motion:** `--dur-1` 100ms (hover/press) · `--dur-2` 160ms (popovers, inspector swap) · `--dur-3` 240ms (drawers, dialogs) · 1.6s marigold wash on newly arrived rows · easing `--ease-out: cubic-bezier(.2,0,0,1)`, `--ease-in-out: cubic-bezier(.4,0,.2,1)` · everything disabled under `prefers-reduced-motion`.

---

## 5. Navigation & information architecture

```
Workspace (switch in user menu)
└─ Property  /p/:propertyId          ← property switcher at top of sidebar
   ├─ Overview      /overview
   ├─ Accounts      /accounts · /accounts/:accountId
   ├─ Discovery     /discovery · /new · /:jobId
   ├─ Contacts      /contacts
   └─ Pipeline      /pipeline
System
   ├─ Properties    /properties · /new · /:id/edit
   ├─ Activity      /activity · /jobs/:jobId · /usage
   └─ Settings      /settings/{workspace,members,providers,scoring,audit}
Everywhere: ⌘K command palette · running-job pill in top bar · inspector on any account row
```

Top bar: breadcrumbs (view name included), search/⌘K, running-job pill, user menu (theme, density, workspace, sign out).

---

## 6. Component inventory

| Component | Key variants / states | Notes |
|---|---|---|
| Button | primary · secondary · ghost · danger; sm/md/lg; icon-only; loading; disabled | One primary per view; labels state the action |
| Input / Select / Combobox | default · focus · invalid (with message) · disabled; prefix/suffix | Label + hint + error slots |
| FilterChip / FilterBar | value chip · add filter · clear all | Serialises to URL query (shareable views) |
| Tabs (saved views) | with counts | |
| SegmentedControl | 2–4 options | Table/Map, density, theme |
| DataTable | sortable headers, sticky header, selection, bulk bar, virtualised rows, comfortable/compact, column picker, loading/empty/error rows | TanStack Table + Virtual |
| Inspector | header, sections, footer actions | Same component in explorer and contacts |
| **EvidenceMark** | Fact (filled) · Inference (half, dashed) · Unknown (empty, dotted); count; source popover (quote, source, dates, grounding result) | Shape encodes certainty without colour |
| **ScoreBar** | Fit (factor segments + legend), Intent (signal segments + freshness), mini table cell | Values come from API breakdown, never recomputed in UI |
| ConfidenceMeter | 5 steps + value + label | Ink, never brand colour |
| **FreshnessTag** | < 90 d marigold · ≥ 90 d neutral · beyond window "Historical" | Thresholds come from scoring model params |
| TierBadge | A · B · C | Lagoon ramp |
| StatusPill | prospecting (6 pips) · opportunity (4 pips) · dismissed · lost | Pips encode lifecycle position |
| DataOriginBadge | Mock (hatched) · Hypothetical (dashed) · Manual | Real data has no badge |
| **RunTimeline** | stage: done · running · pending · failed; counts; progress segments | Driven by job progress API |
| CostMeter | spent · reserved (hatched) · cap | |
| Banner | error · warning · info; actions | Says what happened and what to do |
| EmptyState | title (display), text, primary + secondary action | Every list has one |
| Skeleton | text lines, table rows | |
| Toast | success · error; undo | Level 2 elevation |
| Funnel | horizontal bars to scale | Hand-built SVG/CSS, no chart library (proposed) |
| CommandPalette, Dialog, Drawer, Menu, Popover, Tooltip | Radix primitives styled by tokens | |
| MapPanel | property pin, radius ring, tier-coloured markers | MapLibre |

---

## 7. CSS architecture (D-21: CSS Modules + tokens)

```
frontend/src/design/
  tokens.css        # :root light tokens + dark overrides ([data-theme="dark"] and prefers-color-scheme)
  base.css          # reset, font-face, body text, focus ring, reduced motion, .tnum / .visually-hidden
  fonts/            # self-hosted woff2
frontend/src/components/<Name>/
  <Name>.tsx
  <Name>.module.css # styles for this component only
  <Name>.test.tsx
  index.ts
```

**Rules**
1. Component CSS uses **only tokens** for colour, font, spacing, radius, shadow and duration. No hex values or ad-hoc pixel values (1px hairlines excepted). Enforced by Stylelint (`declaration-strict-value` for colour/spacing properties) in CI.
2. Variants via `data-*` attributes or composed module classes (`data-variant="primary"`, `data-size="sm"`), typed in props.
3. Screens never restyle components. Screen-level `.module.css` holds layout only (grid areas, gaps), using layout primitives `Stack`, `Inline`, `Grid` where possible.
4. Theme: `data-theme` on `<html>` (`light` | `dark`), absent = follow system. Density: `data-density` on the table container.
5. No global class names except the few utilities in `base.css`.
6. Every interactive component has visible focus (2px accent ring, 2px offset) and full keyboard support (Radix provides the behaviour; we provide the look).

---

## 8. Open questions for review

1. Accent hue: Lagoon (deep teal-green) as proposed, or a different brand colour from Inhabitr?
2. Serif display face for titles and quotes (Newsreader), or all-sans?
3. Default density: comfortable (40px rows) as proposed, or compact (32px)?
4. Charts: no chart library for MVP (hand-built funnel, bars, sparklines from tokens); revisit for Analytics. Agree?
