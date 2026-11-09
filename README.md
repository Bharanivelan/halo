# Inhabitr

AI-assisted B2B account intelligence and prospecting for hotel sales teams — starting with pre-opening hotels in India.

> Working name pending trademark clearance. Status: documentation complete; Phase 1 (clickable frontend prototype) next.

Start here: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)

| Doc | |
|---|---|
| [PRD](docs/PRD.md) | Requirements & acceptance criteria |
| [System architecture](docs/SYSTEM_ARCHITECTURE.md) | Components, workflow engine, providers, security, deployment |
| [Agent architecture](docs/AGENT_ARCHITECTURE.md) | Pipeline, research agent, evidence grounding, scoring, budgets |
| [Database schema](docs/DATABASE_SCHEMA.md) | ER diagram & tables |
| [API](docs/API_DOCUMENTATION.md) | REST contract |
| [Roadmap](docs/DEVELOPMENT_ROADMAP.md) | Phases & exit criteria |
| [Decision log](docs/DECISION_LOG.md) | Decisions, proposals, assumptions |
| [Task tracker](docs/TASK_TRACKER.md) | Work items |
| [Eval dataset](data/eval/README.md) | Ground-truth template & instructions |

## Repository rules

- **Never commit secrets.** API keys and credentials live in `.env` files (git-ignored); only `.env.example` with placeholder values is committed.
- **Never commit real customer or researched data.** `data/` is git-ignored except the eval README and template.
- Every architectural change updates the relevant doc and [DECISION_LOG](docs/DECISION_LOG.md) in the same commit.
