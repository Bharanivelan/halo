# Halo: the AI sales agent for hotels

Halo finds the businesses around a hotel, researches them, spots buying signals, scores who is most likely to need
rooms or event space, and drafts the outreach. Every fact it shows carries its source.

> Status: **working MVP** on live public data (OpenStreetMap, company websites, news). Any country; US and India are pinned.

## What's in this repository

| Folder | What |
|---|---|
| [`backend/`](backend) | API (FastAPI), background agent worker, database migrations (Alembic), tests |
| [`web/`](web) | The web app (React, TanStack Start, Tailwind, shadcn/ui), built in Lovable |
| [`docs/`](docs) | Product, architecture, API and agent docs, decision log |
| [`infra/`](infra), [`scripts/`](scripts), `docker-compose.yml` | Local database, one-command dev start, demo tunnel |

How the parts fit together:

```
 web app (localhost:5173)  ──HTTP / bearer token──▶  API (localhost:8000)  ──▶  Postgres + PostGIS (Docker, :5433)
                                                         ▲
                                   background worker ────┘  (runs the agent: discover → research → signals → score)
                                         │
                                         └──▶ OpenStreetMap · company websites · news · Gemini/OpenAI (optional)
```

## Run it locally

### 1. Install the prerequisites

| Tool | Version | Used for |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | any recent | The database. **Keep it running** while you use Halo |
| [Python](https://www.python.org/downloads/) | 3.12 | API and worker |
| [Node.js](https://nodejs.org/) | 20 or newer | Web app tooling |
| [Bun](https://bun.sh/) | 1.x | Installs and runs the web app (`npm install` fails on this project's `rolldown` override) |

### 2. Get the code and configure it

```bash
git clone https://github.com/Bharanivelan/halo.git
cd halo
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

Open `.env` and, if you have one, add an AI key. Everything works without a key (see [what a key adds](#api-keys-and-what-they-unlock)).

```ini
GEMINI_API_KEY=your-key-here      # free key: https://aistudio.google.com/apikey
```

### 3. Start the database

```bash
docker compose up -d db           # Postgres 16 + PostGIS on localhost:5433
```

### 4. Set up the backend (once)

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.cli bootstrap --workspace "Halo" --email you@company.com --name "Your Name"
```

macOS / Linux:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli bootstrap --workspace "Halo" --email you@company.com --name "Your Name"
```

`bootstrap` asks for a password (at least 10 characters) and creates your workspace and your admin login.
Add teammates later with `python -m app.cli add-user --email them@company.com --name "Name" --role manager`.

### 5. Start the API and the worker

Two terminals, both in `backend/` (on macOS / Linux use `.venv/bin/` instead of `.venv\Scripts\`):

```powershell
.venv\Scripts\python -m uvicorn app.main:app --port 8000 --reload --reload-dir app    # terminal 1: API
.venv\Scripts\python -m app.worker                                                      # terminal 2: agent worker
```

API docs (interactive): <http://localhost:8000/api/v1/docs>

### 6. Start the web app

In a third terminal:

```bash
cd web
bun install
```

Then point the app at your local API and start it:

```powershell
# Windows PowerShell
$env:VITE_HALO_API_URL = "http://localhost:8000"; bun run dev --port 5173
```

```bash
# macOS / Linux
VITE_HALO_API_URL=http://localhost:8000 bun run dev --port 5173
```

Open <http://localhost:5173> and sign in with the email and password from step 4.

> To make the API address permanent, put `VITE_HALO_API_URL=http://localhost:8000` in `web/.env.local` (git-ignored).
> You can also change it any time on the sign-in page under **Connection settings**.

### 7. Use it

1. **List a new hotel**: pick the country, search the address, choose what the hotel sells and how far to look.
2. The **agent starts automatically** (up to 50 companies researched, $2 AI spending cap per run). Watch it on the **AI agent** page.
3. Work the **Prospects** list: open a company to see its research, sources, score breakdown and a ready-to-send pitch.
4. Rate leads with 👍 / 👎. Those ratings are the answer key for **Halo Lab**, which tunes the agent.

### Windows shortcut: start everything with one command

After step 4 has been done once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

It starts the database, applies migrations, and opens windows for the API, the worker and the web app
(<http://localhost:5173>). Docker Desktop must already be running.

## Tests

```powershell
cd backend
.venv\Scripts\python -m pytest -q
```

Unit tests plus row-level-security isolation tests run against the local database. **Stop the worker first**: some tests
queue agent jobs and a running worker would pick them up.

Web app checks: `cd web && bun run lint && bunx tsc --noEmit`.

## API keys and what they unlock

| Key (in `.env`) | Without it | With it |
|---|---|---|
| `GEMINI_API_KEY` (or `OPENAI_API_KEY` with `LLM_PROVIDER=openai`) | Companies found and scored from map data and rules; websites fetched but not analysed; template pitches | AI sorting of relevant companies, website research agent, AI buying-signal extraction, written pitches |
| `TAVILY_API_KEY` | Websites only from map / CSV data; news from GDELT only | Finds websites for companies that lack one; more news coverage |

AI spend is capped per run and every AI call is logged with its tokens and cost. The free Gemini tier allows only about
20 requests a day; Halo slows down and falls back to rules when it runs out (set `LLM_MAX_RPM=8` in `.env` for a free key).

## Show it to someone outside your network (optional)

The Lovable-hosted copy of the web app needs a public address for your local API:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\tunnel.ps1
```

Anyone with the tunnel URL can reach the sign-in page (data still needs a login). Stop the tunnel when you are not demoing.
Details: D-37 and D-46 in the [decision log](docs/DECISION_LOG.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sign-in says **"Something went wrong on the server"** | The database isn't running. Start Docker Desktop, then `docker compose up -d db` |
| Sign-in says **"Can't reach the Halo server"** | The API isn't running, or the app points elsewhere: check **Connection settings** on the sign-in page (should be `http://localhost:8000`) |
| `bun run dev` says the port is in use | Pick another port, e.g. `--port 5174`, and allow it in `.env`: `CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]`, then restart the API |
| `npm install` fails in `web/` | Use `bun install` |
| The agent runs but nothing is researched by AI | No AI key, or the free daily allowance is used up. The run still finishes using rules; add a key or wait for the reset |
| Tests fail because jobs were already taken | Stop the worker before running tests |

## Documentation

Start here: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)

| Doc | |
|---|---|
| [PRD](docs/PRD.md) | Requirements and acceptance criteria |
| [System architecture](docs/SYSTEM_ARCHITECTURE.md) | Components, workflow engine, providers, security, deployment |
| [Agent architecture](docs/AGENT_ARCHITECTURE.md) | Pipeline, research agent, evidence grounding, scoring, budgets |
| [Database schema](docs/DATABASE_SCHEMA.md) | ER diagram and tables |
| [API](docs/API_DOCUMENTATION.md) | REST contract (live OpenAPI at `/api/v1/docs`) |
| [Web app (Lovable)](docs/lovable/README.md) | How the web app was built and its typed API kit |
| [Roadmap](docs/DEVELOPMENT_ROADMAP.md) | Phases and exit criteria |
| [Decision log](docs/DECISION_LOG.md) | Every product and architecture decision |
| [Eval dataset](data/eval/README.md) | Ground-truth template and instructions |

## Repository rules

- **Never commit secrets.** Keys and passwords live in `.env` files (git-ignored); only `.env.example` with placeholders is committed. This repository is public.
- **Never commit real customer or researched data.** `data/` is git-ignored except the eval README and template.
- Every architectural change updates the relevant doc and the [decision log](docs/DECISION_LOG.md) in the same commit.
- Development happens in two working repos, combined here with full history: `halo-api` (everything except `web/`) and
  the Lovable-owned app repo (`web/`, via `git subtree`). See D-48 in the [decision log](docs/DECISION_LOG.md).
