# Inhabitr — Project Overview

> Status: **Documentation phase complete → Phase 1 (clickable frontend prototype) next.**
> Last updated: 2026-11-09 · Owner: primary developer · Product name "Inhabitr" is a working name pending trademark clearance (A-10).

## 1. What we are building

Inhabitr is a **B2B account-intelligence and prospecting platform for hotel sales teams**, starting with **pre-opening hotels in India**.

For a given hotel property it answers four questions:

1. **Who** nearby is likely to buy room nights, meetings/events (MICE), long stays or F&B?
2. **Why now?** — what dated, sourced evidence shows demand?
3. **Who should we approach?** — which roles, and (when known) which people?
4. **What should we say?** — a brief and an outreach draft grounded only in verified facts.

…and then tracks whether that work turned into opportunities and revenue.

## 2. Why it matters

A pre-opening hotel has no account base, a fixed opening date and a small sales team expected to build a corporate base 6–12 months before opening. Today that means spreadsheets, manual Google searches and generic pitches. Mid-market companies (≈50–1,000 employees) are the most reachable buyers and the most tedious to research by hand.

Our differentiation is **not** scraping or AI copywriting (both are commodities). It is:

- **Hospitality-specific demand reasoning** — e.g. *inbound* travel (a company headquartered elsewhere with a large local delivery centre generates visitor room nights).
- **Evidence you can inspect** — every fact has a source, a quote, a retrieval date and a verification status.
- **A closed loop** — dismiss reasons and won/lost outcomes are captured from day one so scoring can be calibrated.

## 3. Who it is for (MVP)

| Persona | Role |
|---|---|
| **Sales Manager / Rep** (primary) | Triages ranked accounts, researches, drafts outreach, works pipeline |
| **Manager / Director of Sales (DOS)** | Sets up properties, runs discovery, assigns accounts, reviews pipeline |
| **Workspace Admin** | Users, roles, provider keys, budgets, scoring model |

## 4. MVP in one paragraph

A manager sets up a (hypothetical, clearly labelled) upscale pre-opening hotel in OMR, Chennai with a 15 km radius, offerings and target industries; optionally imports a CSV; sees a cost estimate; and runs discovery. The system discovers companies (CSV, OpenStreetMap, web search), deduplicates and classifies them, researches each with a **bounded research agent** that emits **grounded claims**, extracts **dated signals**, and computes **Fit / Intent / Confidence / Actionability** scores. Users triage accounts in a premium explorer, inspect evidence, add contacts manually, generate on-demand briefs and drafts (copy + "mark sent" — no automated sending), and manage opportunities in a pipeline. Every step's progress, failures and cost are visible.

See [PRD.md](PRD.md) §2 for full scope and out-of-scope list.

## 5. Product principles

1. **AI-first, not AI-dependent.** LLMs reason, extract, classify and write. Code handles data, scoring, permissions, workflow state and integrations.
2. **Human-in-the-loop.** No consequential external action without explicit user action. (MVP sends nothing externally.)
3. **Evidence-driven.** No invented companies, people, numbers, contacts or relationships. Unknown is a valid answer.
4. **Multi-property, tenant-safe.** Workspaces are isolated (app layer + Postgres RLS). A company is stored once per workspace and related to many properties via Accounts.
5. **Extensible by registration.** New steps, providers and prompts are added by registering a class/file, not by rewriting the engine.
6. **Simple until proven otherwise.** Three runtime pieces: web app, worker, Postgres.

## 6. Glossary (P-03 — use these words everywhere)

| Term | Meaning |
|---|---|
| **Workspace** | A tenant (e.g. a hotel management company). All data is scoped to one workspace. |
| **Property** | A hotel. Has location, capacities, offerings, target profile. May be *hypothetical* (demo). |
| **Company** | A prospective customer organisation, stored once per workspace. |
| **Account** | A Company **in relation to** a Property — the lead. Holds prospecting status, owner and scores. |
| **Contact** | A person at a Company (manually entered in MVP). |
| **Opportunity** | A specific deal on an Account (e.g. corporate rate agreement, a 200-person offsite). |
| **Source** | A retrieved document/record (URL, type, retrieval time, licence tag). |
| **Claim** | One statement about a Company, typed FACT / INFERENCE / UNKNOWN, linked to a Source and quote. |
| **Signal** | A dated event implying hospitality demand (office opening, hiring drive, conference…). |
| **Discovery job** | A background workflow that finds, researches and scores companies for a Property. |
| **Offering** | What the hotel sells: `corporate_rate`, `mice`, `long_stay`, `fnb`. |
| **Mock data** | Fabricated sample data, only in the demo workspace, always badged "Mock". |

## 7. Technology summary

React + TypeScript + Vite · FastAPI + Pydantic v2 · SQLAlchemy 2 + Alembic · PostgreSQL + PostGIS (also the job queue and session store) · OpenAI via an LLM gateway abstraction · Docker Compose. Details: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).

## 8. Document map

| Document | Purpose |
|---|---|
| [PRD.md](PRD.md) | Requirements, user journeys, stories, acceptance criteria, NFRs, metrics |
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Components, modules, workflow engine, queue, providers, security, deployment, frontend architecture |
| [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) | Pipeline steps, research agent, claims & grounding, signals, scoring, LLM gateway, budgets & cost estimation |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | ER diagram, tables, enums, indexes, RLS, demo-data separation |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | REST conventions and endpoints |
| [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) | Phases, deliverables, exit criteria, learning topics |
| [DECISION_LOG.md](DECISION_LOG.md) | Confirmed decisions, accepted proposals, open proposals, assumptions register |
| [TASK_TRACKER.md](TASK_TRACKER.md) | Task list by phase with status |
| [../data/eval/README.md](../data/eval/README.md) | Ground-truth evaluation dataset instructions + template |

## 9. Planned repository layout

```
inhabitr/
  docs/                 ← these documents
  data/eval/            ← ground-truth dataset (manually verified)
  frontend/             ← React app (Phase 1 prototype lives here, with a mock API layer)
  backend/              ← FastAPI app + worker (Phase 2+)
  docker-compose.yml    ← Phase 2+
```

## 10. Current status

| Phase | Status |
|---|---|
| 0 — Docs & ground-truth dataset | Docs ✅ · dataset ⏳ (manual, owner) |
| 1 — Design system & clickable prototype | Next |
| 2–5 | Not started |
