# 🛡️ Warranty Shield

Explainable warranty-claim risk triage app with LangGraph integration.

[![Live Demo](https://img.shields.io/badge/🛡️-Live%20Demo-4B7BEC?style=for-the-badge)](https://<your-app-url>.streamlit.app)
[![CI](https://github.com/<your-username>/warranty-shield/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-username>/warranty-shield/actions)

> **👆 Replace `<your-app-url>` and `<your-username>` after deploying — see [DEPLOY.md](DEPLOY.md) for a 5-minute guide to a free public URL.**

Warranty Shield helps warranty teams triage incoming claims by computing an
explainable risk score for every claim, surfacing red flags, and routing
high-risk claims to human review — with an optional agentic workflow built on
LangGraph.

## Features

- **Explainable risk scoring** — every claim gets a 0–100 risk score with a
  full breakdown of contributing factors:
  - Claim amount thresholds
  - Prior claim history (count and total value)
  - Claim category risk (e.g. lost/stolen, accidental damage)
  - Early-claim windows (urgent ≤ 14 days, watch ≤ 30 days after purchase)
  - Red-flag keyword detection in the narrative (lost, stolen, urgent, cash, refund, no receipt, discarded)
  - Missing serial-number penalty
- **Streamlit UI** — submit claims, review a filterable claim table, inspect
  score breakdowns, and act (approve / reject / escalate).
- **LangGraph agent workflow** (optional) — classify → verify → score →
  narrative analysis → decision. Falls back to the scoring engine when
  disabled.
- **Configurable business rules** — all thresholds live in `config.yaml` and
  are validated with Pydantic settings.

## Quick start

Requires Python 3.10+.

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install the package (editable, with dev tools)
pip install -e ".[dev]"

# 3. Configure environment (optional)
cp .env.example .env

# 4. Run the app
streamlit run app/main.py
```

The UI opens at http://localhost:8501.

## 🌐 Host it publicly (resume-ready)

Free one-click hosting from your GitHub repo — the repo ships with everything
needed (`requirements.txt`, `.streamlit/config.toml`, `Dockerfile`).
See **[DEPLOY.md](DEPLOY.md)** for the full walkthrough:

| Platform | Cost | Effort |
| --- | --- | --- |
| **Streamlit Community Cloud** | Free | ⭐ Easiest — deploy from GitHub in 5 min |
| Render / Railway (Docker) | Free tier | Medium |
| Hugging Face Spaces (Docker) | Free | Medium |

## Running tests

```bash
pytest
```

## Linting & type checking

```bash
ruff check app tests
mypy app
```

## Configuration

Business rules and thresholds are centralized in `config.yaml`:

| Section | Purpose |
| --- | --- |
| `scoring` | Risk thresholds, early-claim windows, red-flag keywords, penalties |
| `database` | SQLite database path and connection options |
| `ui` | Streamlit page settings |
| `demo` | Demo-data seeding behaviour |
| `langgraph` | Enable/disable the agentic workflow and its model |

Environment variables (see `.env.example`) override defaults via
`pydantic-settings` (`.env` support included).

## Project structure

```
app/
├── config/        # Pydantic settings and business-rule configuration
├── models/        # Pydantic data models (claims, scoring results, events)
├── services/      # Scoring engine, claim service, LangGraph agent
├── ui/            # Streamlit interface
├── utils/         # Logging, formatting, and helper utilities
└── main.py        # Streamlit entry point
tests/             # pytest suite
scripts/           # Helper scripts
data/              # SQLite database location
```

## License

MIT
