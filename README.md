# FairGuard — AI Fairness Firewall & Audit Platform

FairGuard is a comprehensive middleware and governance layer designed to inspect datasets and AI/ML models for unfair discrimination. It enforces fairness contracts during CI/CD pipelines, monitors live decision traffic for bias in production, and issues cryptographically signed fairness receipts.

## Features

- **Project & Fairness Contract Management**: Full CRUD capabilities for configuring projects with rigorous fairness contracts (evaluating disparate impact, TPR/FPR gaps, and accuracy gaps) including versioning and metric validation.
- **Offline Dataset & Model Audit**: Upload CSV datasets, analyze per-group fairness metrics leveraging Fairlearn and Numpy, and evaluate against your contracts giving PASS, FAIL, or WARN verdicts.
- **Runtime Fairness Firewall**: Ingest live AI decision data using sliding windows, enabling continuous monitoring of fairness metrics and providing automated alert thresholds when bounds are breached.
- **Fairness Receipts & Attestations**: Automatically generate Ed25519 verifiable cryptographically-signed records ("receipts") logging the fairness status of your ML audits.
- **Interactive React Dashboard**: A clear visual reporting tool with traffic-light status indicators, detailed bar charts, real-time metrics time-series, and plain-language metric explanations so non-technical stakeholders can understand the bias.
- **CI/CD CLI & Extensible SDK**: The `fairguard-cli` pip package allowing easy automated integration into your build/deployment pipelines, and a Python SDK for programmatic runtime access.
- **Enterprise-ready Authentication & Authorization**: Secure JWT-based auth, scoped API keys, and role-based access control policies (admin, project_owner, viewer).

---

## Tech Stack Overview

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, asyncpg, Celery
- **AI/Fairness**: Fairlearn, AIF360, Numpy, Pandas, Scikit-learn
- **Database Architecture**: PostgreSQL 15, Redis 7 (task broker + caching)
- **Frontend SPA**: React 18, TypeScript, Vite, Tailwind CSS, Recharts
- **Security & Encryption**: JWT (HS256), bcrypt, Ed25519 (for signing receipts)
- **Container**: Docker, Docker Compose

---

## Quick Start

### Prerequisites

- Docker & Docker Compose v2+
- Python 3.10+ (for CLI / SDK)

### 1. Clone & configure

```bash
git clone https://github.com/yourorg/fairguard.git
cd fairguard

# Copy and edit the environment file
cp .env.example .env
# At minimum, change SECRET_KEY:
#   python -c "import secrets; print(secrets.token_hex(32))"
nano .env
```

Also create `frontend/.env`:
```bash
# fairguard/frontend/.env
VITE_API_URL="http://localhost:8000/api/v1"
```

### 2. Start all services

```bash
docker compose up -d --build
```

This will:
1. Start Postgres and Redis
2. Build and start the backend (runs `alembic upgrade head` automatically)
3. Build and start the frontend
4. Start the Celery worker
5. Start Nginx on port 80

### 3. Open the dashboard

Visit **http://localhost** in your browser.

Default admin credentials (configurable in `.env`):
- Email: `admin@fairguard.local`
- Password: `changeme123`

### 4. API Documentation

FastAPI auto-docs are available at:
- Swagger UI: **http://localhost:8000/api/v1/docs**
- ReDoc: **http://localhost:8000/api/v1/redoc**

---

## CLI Usage

Provide the tool with your generated API key (created from inside the Web App Dashboard):

```bash
pip install fairguard-cli
fairguard init
fairguard test --data predictions.csv --target actual_label --prediction model_score --sensitive gender,race

# Check runtime status
fairguard status --project-id <your-ui-project-id>
```

### Initialize (non-interactive for CI)

```bash
fairguard init \
  --api-url http://your-fairguard-instance/api/v1 \
  --api-key fg_your_api_key \
  --no-interactive
```

### Run a fairness audit

```bash
fairguard test \
  --data predictions.csv \
  --project-id your-project-id \
  --target actual_label \
  --prediction model_score \
  --sensitive gender,age_group
```

Exit codes: `0` = pass, `1` = pass with warnings, `2` = fail.

### Download an audit report

```bash
# PDF report
fairguard report --audit-id <id> --format pdf --output report.pdf

# Markdown report
fairguard report --audit-id <id> --format markdown --output report.md
```

### Check runtime status

```bash
fairguard status --project-id your-project-id
```

### Manage receipts

```bash
# List receipts
fairguard receipts list --project-id your-project-id

# Verify a receipt's cryptographic signature
fairguard receipts verify --receipt-id <receipt-id>
```

---

## SDK Usage

### Install

```bash
pip install fairguard-sdk
```

### Audit a model batch

```python
import asyncio
import pandas as pd
from fairguard_sdk import FairGuardClient

async def main():
    async with FairGuardClient(
        api_url="http://localhost:8000/api/v1",
        api_key="fg_your_api_key"
    ) as client:
        df = pd.read_csv("predictions.csv")
        result = await client.run_audit(
            project_id="your-project-id",
            data=df,
            target_col="actual_label",
            prediction_col="model_score",
            sensitive_cols=["gender", "age_group"]
        )
        print(f"Verdict: {result.verdict}")

asyncio.run(main())
```

### LLM Pipeline Integration

```python
from fairguard_sdk import FairGuardClient

async def monitor_pipeline():
    async with FairGuardClient(api_url=URL, api_key=KEY) as client:
        await client.ingest_decisions_async(
            project_id="proj-id",
            decisions=[{
                "decision_id": "d-001",
                "sensitive_attributes": {"gender": "F"},
                "outcome": "1",
                "timestamp": "2024-01-15T10:00:00Z"
            }]
        )
        status = await client.get_runtime_status_async("proj-id")
        if status.overall_status == "critical":
            raise RuntimeError("Fairness critical — halting pipeline")
```

---

## CI/CD Integration

See [docs/ci-examples.md](docs/ci-examples.md) for full examples.

### GitHub Actions

```yaml
- name: Run Fairness Audit
  uses: actions/checkout@v4
- run: pip install fairguard-cli
- run: |
    fairguard init --api-url ${{ secrets.FAIRGUARD_API_URL }} \
      --api-key ${{ secrets.FAIRGUARD_API_KEY }} --no-interactive
    fairguard test --data predictions.csv --project-id ${{ secrets.FAIRGUARD_PROJECT_ID }} \
      --target actual --prediction predicted --sensitive gender,race
```

### GitLab CI

```yaml
fairness-gate:
  stage: test
  image: python:3.11
  script:
    - pip install fairguard-cli
    - fairguard init --api-url $FAIRGUARD_URL --api-key $FAIRGUARD_KEY --no-interactive
    - fairguard test --data outputs/predictions.csv --project-id $PROJECT_ID
        --target actual --prediction predicted --sensitive gender,race
  allow_failure: false
```

---

## Project Architecture

```
fairguard/
├── backend/          # FastAPI app (Python 3.11)
│   ├── api/v1/       # Route handlers (auth, projects, contracts, audits, runtime, receipts)
│   ├── services/     # Business logic (fairness metrics, Ed25519 signing, alerts, runtime monitor)
│   ├── models/       # SQLAlchemy ORM models
│   └── core/         # Config, auth (JWT), database, Pydantic schemas
├── frontend/         # React SPA (TypeScript + Tailwind + Recharts)
│   └── src/
│       ├── api/      # Axios API client
│       ├── pages/    # Dashboard, Projects, Audits, Runtime, Receipts
│       └── components/ # Charts, MetricCards, TrafficLight, VerdictBadge
├── cli/              # fairguard-cli pip package (Typer)
├── sdk/              # fairguard-sdk pip package
├── docker/           # Dockerfiles + nginx config
│   ├── backend/Dockerfile
│   ├── frontend/Dockerfile
│   └── nginx/nginx.conf
└── docs/             # API reference, CI examples, usage guide
```

**Services (docker-compose):**
- `postgres` — PostgreSQL 15 (persistent storage)
- `redis` — Redis 7 (task broker + caching)
- `backend` — FastAPI + Uvicorn (API server, runs migrations on start)
- `celery-worker` — Celery worker (async fairness computations)
- `frontend` — React app built by Nginx
- `nginx` — Reverse proxy (port 80 → backend API + frontend SPA)

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✓ | JWT secret key (min 32 chars) |
| `ALGORITHM` | | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Token TTL (default: `1440`) |
| `DATABASE_URL` | ✓ | PostgreSQL connection string |
| `REDIS_URL` | ✓ | Redis URL for caching |
| `CELERY_BROKER_URL` | ✓ | Celery broker URL |
| `CELERY_RESULT_BACKEND` | ✓ | Celery result backend URL |
| `SIGNING_KEY_PATH` | | Ed25519 private key PEM path (default: `/app/keys/ed25519_private.pem`) |
| `SMTP_HOST` | | SMTP server host for alerts |
| `SMTP_PORT` | | SMTP port (default: `587`) |
| `SMTP_USER` | | SMTP username |
| `SMTP_PASSWORD` | | SMTP password |
| `SMTP_FROM` | | From address (default: `noreply@fairguard.local`) |
| `CORS_ORIGINS` | | JSON array of allowed CORS origins |
| `FIRST_ADMIN_EMAIL` | | Seed admin email (default: `admin@fairguard.local`) |
| `FIRST_ADMIN_PASSWORD` | | Seed admin password (default: `changeme123`) |

## License

Apache 2.0