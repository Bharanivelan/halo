# Halo API

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
.venv/Scripts/python -m app.cli bootstrap --workspace "Halo" --email you@company.com --name "Your Name"
.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload --reload-dir app     # API  → http://localhost:8000/api/v1/docs
.venv/Scripts/python -m app.worker                                                       # worker (second terminal)

# 4. A frontend: the Lovable app (halo-web, see docs/lovable) or the classic UI:
cd ../halo-web-classic && npm install && npm run dev                                     # app  → http://localhost:5173

# 5. Optional: public URL for the Lovable-hosted app to reach this API
powershell -ExecutionPolicy Bypass -File scripts/tunnel.ps1
```

Accounts: `bootstrap` creates the first admin from the command line. People can also create their own account in the app
(**Create an account** on the sign-in page, `/signup`); each sign-up gets its own workspace. Set `SIGNUP_ENABLED=false` for an
invite-only server and add people with `python -m app.cli add-user --email … --name … --role rep|manager|admin`.

Tests: `cd backend && .venv/Scripts/python -m pytest -q` (unit tests + row-level-security isolation tests against the dev DB).

### API keys and what they unlock

| Key | Without it | With it |
|---|---|---|
| An AI provider: Gemini, OpenAI, **Amazon Bedrock** or any OpenAI-compatible server ([choose one](#choose-an-ai-provider)) | Companies found and scored from map data and rules; website fetched but not analysed; template drafts | AI classification, website research agent, AI signal extraction, grounded email drafts, plain-language job setup |
| `TAVILY_API_KEY` | Websites only from map/CSV data; news from GDELT only | Finds websites for companies that lack one; extra news coverage |

Spend is capped per job (you set the budget) and every AI call is logged with tokens and cost (Activity page).

## Choose an AI provider

Halo works with four kinds of AI provider. Pick one with `LLM_PROVIDER` in `.env` and restart the API and worker.
Without any AI, Halo still runs on map data and rules.

| `LLM_PROVIDER` | Use it for | What to set in `.env` | Default models |
|---|---|---|---|
| `gemini` (default) | Google Gemini; has a free tier | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| `openai` | OpenAI | `OPENAI_API_KEY` | `gpt-5-mini` |
| `bedrock` | **Amazon Bedrock**: Claude, Nova, Llama, Mistral and other models in your AWS account | AWS credentials (below) and `AWS_REGION` | `amazon.nova-lite-v1:0` (fast), `amazon.nova-pro-v1:0` (standard) |
| `openai_compatible` | Any OpenAI-style server: OpenRouter, Groq, Together, Azure OpenAI, Ollama, LM Studio, vLLM | `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY` (empty for local servers), `LLM_MODEL_FAST` | none: you choose |

Halo uses two model sizes: `LLM_MODEL_FAST` sorts and extracts, `LLM_MODEL_STANDARD` researches websites and writes.
Leave them empty to use the defaults above, or set your own.

### Amazon Bedrock

1. In the AWS console, open **Amazon Bedrock → Model access** in your region and enable the models you want.
2. Give Halo credentials in **one** of these ways:
   - an AWS profile or SSO login on this machine: `AWS_PROFILE=my-profile` (run `aws sso login` first if you use SSO);
   - access keys: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (plus `AWS_SESSION_TOKEN` for temporary keys);
   - a Bedrock API key (Bedrock console → API keys): `AWS_BEARER_TOKEN_BEDROCK`;
   - nothing at all when Halo runs on AWS with an IAM role (EC2, ECS, Lambda).
   The identity needs the `bedrock:InvokeModel` permission.
3. Set the region and, optionally, the models:

```ini
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_PROFILE=my-profile
# Optional: any Bedrock chat model or inference profile ID from the Bedrock model catalog, e.g.
# LLM_MODEL_FAST=amazon.nova-lite-v1:0
# LLM_MODEL_STANDARD=<a Claude model or inference profile ID from your Bedrock console>
```

Some models can only be called through a cross-region **inference profile** (an ID that starts with `us.`, `eu.` or
`apac.`). If Halo says so, use the profile ID from the console. Halo adapts to models that can't force a tool, take no
system prompt or have a smaller output limit. AI cost is estimated from `LLM_PRICING`; models not listed there are
estimated at $1 / $4 per million input / output tokens. To make the cost figures exact, set your model's prices (this replaces the built-in price list):
`LLM_PRICING={"us.anthropic.your-model-id": [3.0, 15.0]}`.

### OpenAI-compatible servers

```ini
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api/v1      # Ollama: http://localhost:11434/v1
OPENAI_COMPATIBLE_API_KEY=your-key                           # empty for Ollama / LM Studio
LLM_MODEL_FAST=the-model-name                                # used for both sizes if LLM_MODEL_STANDARD is empty
```

The research agent needs a model that supports **tool calling** (function calling). Small local models without it
still sort and score companies, but website research will be weak.

## Documentation

Start here: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)

| Doc | |
|---|---|
| [PRD](docs/PRD.md) | Requirements & acceptance criteria |
| [System architecture](docs/SYSTEM_ARCHITECTURE.md) | Components, workflow engine, providers, security, deployment |
| [Agent architecture](docs/AGENT_ARCHITECTURE.md) | Pipeline, research agent, evidence grounding, scoring, budgets |
| [Database schema](docs/DATABASE_SCHEMA.md) | ER diagram & tables |
| [Deployment](docs/DEPLOYMENT.md) | Host it: Supabase (database) + Railway (API, worker) |
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
