# Halo API (by Inhabitr)

Backend for **Halo**, the AI go-to-market agent for multi-location hotel and restaurant groups: discover the companies
around each location, research them, detect buying signals, score them, recommend whom to approach and draft the pitch.
Starting with pre-opening hotels in India.

> Status: **working MVP**. Real discovery, research, scoring, copilot and pipeline on live public data.

## Repositories (D-35)

| Repo | What | Where |
|---|---|---|
| **halo-api** (this repo) | FastAPI API, background agent worker, Postgres/PostGIS, docs | here |
| **halo-web** | The Halo web app, built in Lovable (React + Tailwind + shadcn), talks to this API with a bearer token | Lovable → GitHub |
| halo-web-classic | The first React UI (CSS Modules). Kept as a fallback; uses cookie auth via a Vite proxy | sibling folder `../halo-web-classic` |

Building the Lovable UI: [docs/lovable/README.md](docs/lovable/README.md).

## What it does

1. You set up a hotel (location, capacities, what it sells, target industries, radius).
2. A discovery job (the GTM agent) runs in the background:
   **plan → discover companies (OpenStreetMap, your CSV) → de-duplicate → classify → research each website (bounded AI agent) → find dated business signals (news + site) → score Fit / Intent / Confidence**.
   Every fact is stored with its source URL, retrieval date and an exact quote. Quotes that can't be found in the source are downgraded to *Unknown* automatically.
3. Your team works ranked accounts in the explorer, adds contacts, generates grounded outreach drafts (sent manually from your own mailbox), and tracks opportunities.

## Run it locally

Prerequisites: Docker Desktop, Python 3.12, Node 20+.

```bash
# 1. Configuration
cp .env.example .env            # then set GEMINI_API_KEY (strongly recommended) and optionally TAVILY_API_KEY

# 2. Database (Postgres 16 + PostGIS on localhost:5433)
docker compose up -d db

# 3. Backend
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m app.cli bootstrap --workspace "Inhabitr" --email you@company.com --name "Your Name"
.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload --reload-dir app     # API  → http://localhost:8000/api/v1/docs
.venv/Scripts/python -m app.worker                                                       # worker (second terminal)

# 4. A frontend: the Lovable app (halo-web, see docs/lovable) or the classic UI:
cd ../halo-web-classic && npm install && npm run dev                                     # app  → http://localhost:5173

# 5. Optional: public URL for the Lovable-hosted app to reach this API
powershell -ExecutionPolicy Bypass -File scripts/tunnel.ps1
```

Tests: `cd backend && .venv/Scripts/python -m pytest -q` (unit tests + row-level-security isolation tests against the dev DB).

### API keys and what they unlock

| Key | Without it | With it |
|---|---|---|
| `GEMINI_API_KEY` (or `OPENAI_API_KEY` with `LLM_PROVIDER=openai`) | Companies found and scored from map data and rules; website fetched but not analysed; template drafts | AI classification, website research agent, AI signal extraction, grounded email drafts, plain-language job setup |
| `TAVILY_API_KEY` | Websites only from map/CSV data; news from GDELT only | Finds websites for companies that lack one; extra news coverage |

Spend is capped per job (you set the budget) and every AI call is logged with tokens and cost (Activity page).

## Documentation

Start here: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)

| Doc | |
|---|---|
| [PRD](docs/PRD.md) | Requirements & acceptance criteria |
| [System architecture](docs/SYSTEM_ARCHITECTURE.md) | Components, workflow engine, providers, security, deployment |
| [Agent architecture](docs/AGENT_ARCHITECTURE.md) | Pipeline, research agent, evidence grounding, scoring, budgets |
| [Database schema](docs/DATABASE_SCHEMA.md) | ER diagram & tables |
| [API](docs/API_DOCUMENTATION.md) | REST contract (live OpenAPI at `/api/v1/docs`) |
| [Design system](docs/DESIGN_SYSTEM.md) | Tokens, components, CSS rules |
| [Roadmap](docs/DEVELOPMENT_ROADMAP.md) | Phases & exit criteria |
| [Decision log](docs/DECISION_LOG.md) | Decisions, proposals, assumptions |
| [Task tracker](docs/TASK_TRACKER.md) | Work items |
| [Eval dataset](data/eval/README.md) | Ground-truth template & instructions |

## Repository rules

- **Never commit secrets.** API keys and credentials live in `.env` files (git-ignored); only `.env.example` with placeholder values is committed.
- **Never commit real customer or researched data.** `data/` is git-ignored except the eval README and template.
- Every architectural change updates the relevant doc and [DECISION_LOG](docs/DECISION_LOG.md) in the same commit.
