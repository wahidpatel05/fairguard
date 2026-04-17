# FairGuard — AI Fairness Firewall & Audit Platform

FairGuard is a middleware and governance layer that inspects datasets and AI/ML models for unfair discrimination, enforces fairness contracts during CI/CD pipelines, monitors live decision traffic for bias in production, and issues verifiable, cryptographically signed fairness receipts.

## Features

- **Project & Fairness Contract Management** — CRUD for projects with configurable fairness contracts (disparate impact, TPR/FPR gaps, accuracy gaps) with versioning and validation
- **Offline Dataset & Model Audit** — Upload CSV datasets, compute per-group fairness metrics with Fairlearn/numpy, evaluate contracts with PASS/FAIL/WARN verdicts
- **Runtime Fairness Firewall** — Ingest live decision data, maintain rolling windows, monitor metrics continuously with alert thresholds
- **Fairness Receipts & Attestations** — Auto-generate Ed25519-signed fairness receipts after each audit, verifiable via API
- **React Dashboard** — Visual reporting with traffic-light indicators, bar charts, time-series charts, and plain-language metric explanations
- **CLI & SDK** — `fairguard-cli` pip package for CI/CD integration, Python SDK for programmatic access
- **Authentication & Authorization** — JWT auth, role-based access (admin/project_owner/viewer), API keys

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for CLI)

### Run with Docker

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your settings (generate SECRET_KEY at minimum)

# Start all services
docker-compose up -d

# Backend API: http://localhost:8000
# Frontend:    http://localhost:3000
# API Docs:    http://localhost:8000/docs
```

### Install CLI

```bash
pip install fairguard-cli

# Initialize project
fairguard init

# Run a fairness audit
fairguard test --data predictions.csv --target label --prediction score --sensitive gender,age_group

# Check runtime status
fairguard status --project-id <id>
```

## Architecture

```
fairguard/
├── backend/          # FastAPI app (Python)
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
└── docs/             # API reference, CI examples, usage guide
```

## API Reference

All APIs versioned at `/api/v1/...`. See [docs/api-reference.md](docs/api-reference.md) for full documentation.

Key endpoints:
- `POST /api/v1/audit/offline` — Upload CSV, run fairness audit
- `POST /api/v1/runtime/ingest` — Ingest live decisions
- `GET /api/v1/runtime/status` — Current fairness status
- `GET /api/v1/receipts/{id}` — Get signed fairness receipt
- `POST /api/v1/receipts/{id}/verify` — Verify receipt signature

## CI/CD Integration

See [docs/ci-examples.md](docs/ci-examples.md) for GitHub Actions and GitLab CI examples.

```yaml
# GitHub Actions snippet
- name: Run Fairness Audit
  run: fairguard test --data predictions.csv --target label --prediction score --sensitive gender
  env:
    FAIRGUARD_API_KEY: ${{ secrets.FAIRGUARD_API_KEY }}
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, asyncpg
- **Fairness**: Fairlearn, numpy/pandas (manual fallback)
- **Database**: PostgreSQL 15, Redis 7
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts
- **Auth**: JWT (HS256), bcrypt, Ed25519 (receipt signing)
- **Container**: Docker, Docker Compose, Kubernetes-compatible

## License

Apache 2.0