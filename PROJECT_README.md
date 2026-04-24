# FairGuard — Comprehensive Project Guide

> This document is the single authoritative reference for AI agents and developers working on the FairGuard codebase. It covers architecture, setup, core logic, conventions, and agent-specific guidance.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Structure](#2-architecture--structure)
3. [Dependencies & Setup](#3-dependencies--setup)
4. [Core Logic & Workflows](#4-core-logic--workflows)
5. [Common Issues & Solutions](#5-common-issues--solutions)
6. [Code Conventions & Standards](#6-code-conventions--standards)
7. [Development Guidelines](#7-development-guidelines)
8. [Agent-Specific Instructions](#8-agent-specific-instructions)

---

## 1. Project Overview

### Name & Purpose

**FairGuard** is an AI Fairness Firewall and Audit Platform. It acts as a middleware and governance layer that inspects datasets and ML model outputs for unfair discrimination, enforces configurable fairness contracts, and continuously monitors live AI decision traffic for bias.

### High-Level Description

FairGuard provides three complementary modes of fairness governance:

| Mode | Description |
|------|-------------|
| **Offline audit** | Upload a CSV of model predictions and ground-truth labels; FairGuard computes fairness metrics and evaluates them against a project's fairness contract. |
| **Runtime firewall** | Ingest live model decision events via API or SDK; FairGuard maintains sliding-window metrics and raises alerts when thresholds are breached. |
| **Fairness receipts** | Every offline audit automatically produces a cryptographically signed Ed25519 receipt providing tamper-evident proof of the audit outcome. |

### Target Users / Audience

- **ML engineers** integrating fairness gates into CI/CD pipelines via the CLI or SDK.
- **Data scientists** running ad-hoc bias investigations via the REST API or dashboard.
- **Compliance / legal teams** consuming signed receipts as audit evidence.
- **Platform administrators** managing users, projects, API keys, and alert rules via the dashboard.

### Key Features

- **Project & Fairness Contract Management** — Full CRUD for projects with versioned fairness contracts (disparate impact, TPR/FPR gaps, accuracy gaps).
- **Offline Dataset & Model Audit** — Upload CSV datasets, compute per-group Fairlearn metrics, evaluate against contracts, and receive PASS / FAIL / PASS_WITH_WARNINGS verdicts.
- **Runtime Fairness Firewall** — Sliding-window monitoring (last 100, last 1 000, last 1 hr, last 24 hr) with automated threshold alerting.
- **Fairness Receipts & Attestations** — Ed25519-signed records of every audit outcome.
- **Interactive React Dashboard** — Traffic-light status indicators, bar charts, time-series metrics, and plain-language explanations.
- **CI/CD CLI (`fairguard-cli`)** — Pip-installable CLI integrating with GitHub Actions, GitLab CI, and any shell-based pipeline.
- **Python SDK (`fairguard-sdk`)** — Programmatic access for runtime ingestion and audit automation.
- **Enterprise Auth & RBAC** — JWT-based auth, bcrypt passwords, scoped API keys, and roles (`admin`, `project_owner`, `viewer`).

---

## 2. Architecture & Structure

### Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend API** | Python 3.11, FastAPI 0.111, Uvicorn, SQLAlchemy 2.0 (async), Alembic, asyncpg |
| **Task Queue** | Celery 5.4, Redis 7 (broker + result backend) |
| **Fairness Computation** | Fairlearn 0.10, AIF360 0.6, NumPy 1.26, Pandas 2.2, scikit-learn 1.5 |
| **Security** | python-jose (JWT HS256), passlib + bcrypt, PyNaCl (Ed25519 receipt signing) |
| **Database** | PostgreSQL 15 |
| **Cache / Session Blacklist** | Redis 7 |
| **Frontend** | React 19 (TypeScript), Vite 8, Tailwind CSS 3, Recharts 3, React Query 5, Axios |
| **Container** | Docker, Docker Compose v2 |
| **Reverse Proxy** | Nginx (Alpine) |
| **CLI** | Typer, Rich |
| **Report Generation** | ReportLab (PDF), Markdown |

### Project Folder Structure

```
fairguard/
├── .env.example              # Template for all environment variables
├── docker-compose.yml        # Orchestrates all 6 services
├── patch.py                  # One-off utility/patch script
│
├── backend/                  # Python 3.11 FastAPI application
│   ├── main.py               # Entrypoint: re-exports `app` from app.main
│   ├── requirements.txt      # All Python dependencies (pinned)
│   ├── alembic.ini           # Alembic configuration
│   ├── alembic/              # Database migrations
│   │   ├── env.py            # Migration env — imports app.* models/settings
│   │   └── versions/         # Individual migration files
│   │
│   ├── app/                  # Main application package
│   │   ├── main.py           # FastAPI app factory, lifespan, middleware
│   │   ├── celery_app.py     # Celery application instance
│   │   │
│   │   ├── api/v1/           # Route handlers (one file per resource)
│   │   │   ├── router.py     # Aggregates all sub-routers
│   │   │   ├── auth.py       # POST /auth/register, /auth/login, /auth/logout, GET /auth/me
│   │   │   ├── users.py      # User management (admin only)
│   │   │   ├── projects.py   # Project CRUD
│   │   │   ├── contracts.py  # Fairness contract versioning
│   │   │   ├── audits.py     # Offline audit upload + results
│   │   │   ├── runtime.py    # Decision ingestion + runtime status
│   │   │   ├── receipts.py   # Fetch + verify signed receipts
│   │   │   ├── api_keys.py   # API key management
│   │   │   ├── notifications.py # Alert configuration
│   │   │   └── reports.py    # PDF/Markdown report generation
│   │   │
│   │   ├── core/             # Cross-cutting infrastructure
│   │   │   ├── base.py       # SQLAlchemy declarative Base (side-effect free)
│   │   │   ├── config.py     # Pydantic Settings (reads .env)
│   │   │   ├── database.py   # Async engine, SessionLocal, get_db(), get_redis()
│   │   │   ├── security.py   # JWT helpers, bcrypt, API key verification, auth deps
│   │   │   └── deps.py       # Reusable FastAPI dependencies (e.g. require_project_access)
│   │   │
│   │   ├── models/           # SQLAlchemy ORM models
│   │   │   ├── user.py       # User (roles: admin, project_owner, viewer)
│   │   │   ├── project.py    # Project (domains: hiring, lending, healthcare, other)
│   │   │   ├── contract.py   # FairnessContract (versioned, one is_current per project)
│   │   │   ├── audit.py      # OfflineAudit (stores metrics_json + verdict)
│   │   │   ├── receipt.py    # FairnessReceipt (Ed25519 signed payload)
│   │   │   ├── runtime.py    # RuntimeDecision + RuntimeSnapshot (sliding windows)
│   │   │   ├── api_key.py    # APIKey (bcrypt-hashed, scoped to project/user)
│   │   │   └── notification.py # NotificationConfig + NotificationLog
│   │   │
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   │
│   │   ├── services/         # Business logic
│   │   │   ├── fairness.py   # FairnessEngine: compute_metrics, evaluate_contracts, compute_verdict
│   │   │   ├── receipt.py    # ReceiptService: Ed25519 signing + DB persistence
│   │   │   ├── runtime.py    # Window queries, snapshot computation, status aggregation
│   │   │   ├── notifications.py # Email/webhook alert dispatch
│   │   │   └── reports.py    # PDF/Markdown report builder
│   │   │
│   │   └── tasks/            # Celery async tasks
│   │
│   ├── core/                 # Legacy core (pre-app refactor — still present)
│   ├── models/               # Legacy models (pre-app refactor — still present)
│   ├── api/                  # Legacy API routes (pre-app refactor — still present)
│   └── services/             # Legacy services (used by FairnessEngine via import alias)
│
├── frontend/                 # React 19 + TypeScript SPA
│   ├── src/
│   │   ├── api/              # Axios API client wrappers
│   │   ├── pages/            # Dashboard, Projects, Audits, Runtime, Receipts
│   │   ├── components/       # Charts, MetricCards, TrafficLight, VerdictBadge
│   │   └── types/            # TypeScript type definitions
│   ├── index.html
│   └── vite.config.ts
│
├── cli/                      # fairguard-cli pip package (Typer-based)
│   ├── src/
│   └── pyproject.toml
│
├── sdk/                      # fairguard-sdk pip package
│   ├── src/
│   └── pyproject.toml
│
├── docker/                   # Container build files
│   ├── backend/Dockerfile
│   ├── frontend/Dockerfile
│   └── nginx/nginx.conf
│
└── docs/                     # User-facing documentation
    ├── api-reference.md
    ├── ci-examples.md
    └── usage-guide.md
```

### Key Files and Their Purposes

| File | Purpose |
|------|---------|
| `backend/main.py` | Uvicorn entrypoint — re-exports `app` from `app.main` |
| `backend/app/main.py` | FastAPI app factory — registers routers, CORS, lifespan startup/shutdown |
| `backend/app/core/config.py` | `Settings` class (pydantic-settings) — source of truth for all env vars |
| `backend/app/core/database.py` | Creates async engine, provides `get_db()` and `get_redis()` FastAPI deps |
| `backend/app/core/base.py` | `Base = declarative_base()` — imported by all ORM models; side-effect free |
| `backend/alembic/env.py` | Alembic migration environment — imports `app.*` models so they are detected |
| `backend/app/services/fairness.py` | `FairnessEngine` — core bias computation using Fairlearn + scikit-learn |
| `backend/app/services/receipt.py` | `ReceiptService` — Ed25519 signing/verification + receipt DB persistence |
| `backend/app/services/runtime.py` | Window queries, snapshot upsert, and overall status aggregation |
| `docker-compose.yml` | Defines all 6 services (postgres, redis, backend, celery-worker, frontend, nginx) |
| `.env.example` | Template listing every supported environment variable |

### Database Schema

All tables use UUID primary keys generated by PostgreSQL's `gen_random_uuid()`.

```
users
  id (UUID PK)  email (unique)  hashed_password  full_name
  role (admin|project_owner|viewer)  is_active  created_at  updated_at

projects
  id (UUID PK)  name  description  owner_id → users.id
  domain (hiring|lending|healthcare|other)  created_at  updated_at

fairness_contracts
  id (UUID PK)  project_id → projects.id  version (int)
  is_current (bool)  contracts_json (JSONB)  created_by → users.id
  created_at  notes
  UNIQUE (project_id, version)

offline_audits
  id (UUID PK)  project_id → projects.id
  contract_version_id → fairness_contracts.id
  dataset_filename  dataset_hash  target_column  prediction_column
  sensitive_columns (TEXT[])  metrics_json (JSONB)
  verdict (pass|fail|pass_with_warnings)
  triggered_by (api|cli)  user_id → users.id  created_at

fairness_receipts
  id (UUID PK)  audit_id → offline_audits.id (unique)
  project_id → projects.id  model_endpoint_id  dataset_hash
  contract_version  contracts_summary (JSONB)  metrics_summary (JSONB)
  verdict  signed_payload  signature  public_key  onchain_tx_id  created_at

runtime_decisions
  id (UUID PK)  project_id → projects.id  model_endpoint_id
  aggregation_key  decision_id  sensitive_attributes (JSONB)
  outcome  ground_truth  timestamp  ingested_at

runtime_snapshots
  id (UUID PK)  project_id → projects.id  aggregation_key
  window_type (last_100|last_1000|last_1hr|last_24hr)
  metrics_json (JSONB)  status (healthy|warning|critical)  evaluated_at
  UNIQUE (project_id, aggregation_key, window_type)

api_keys
  id (UUID PK)  user_id → users.id  project_id → projects.id
  key_hash  name  is_active  last_used_at  created_at

notification_configs / notification_logs
  (alert webhook/email configuration per project)
```

### API Endpoints Summary

All routes are prefixed with `/api/v1`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login, receive JWT |
| GET | `/auth/me` | Current user info |
| POST | `/auth/logout` | Invalidate JWT via Redis blacklist |
| GET/POST/PUT/DELETE | `/projects` | Project CRUD |
| GET/POST/PUT | `/contracts` | Fairness contract versioning |
| POST | `/audit/offline` | Upload CSV and run offline audit |
| GET | `/audit/offline` | List audits for a project |
| GET | `/audit/offline/{audit_id}` | Fetch audit with full metrics |
| POST | `/runtime/ingest` | Ingest batch of runtime decisions |
| GET | `/runtime/status` | Get current runtime snapshot status |
| GET | `/receipts/{receipt_id}` | Fetch a signed receipt |
| POST | `/receipts/{receipt_id}/verify` | Verify receipt cryptographic signature |
| GET | `/reports/...` | Generate PDF or Markdown reports |
| GET/POST/DELETE | `/api-keys` | API key management |
| GET/POST/DELETE | `/notifications` | Notification configuration |
| GET/PUT/DELETE | `/users` | User management (admin only) |

---

## 3. Dependencies & Setup

### Required Software & Versions

| Tool | Minimum Version | Required For |
|------|----------------|--------------|
| Docker | 24.x | Container runtime |
| Docker Compose | v2.x (`docker compose`) | All-in-one startup |
| Python | 3.11 | Local backend / CLI / SDK dev |
| Node.js | 22.x | Local frontend dev |
| npm | 10.x | Frontend package management |
| PostgreSQL | 15 | Database (handled by Docker) |
| Redis | 7 | Cache + Celery broker (handled by Docker) |

### Environment Variables

Copy `.env.example` to `.env` and set these values:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | — | JWT signing secret (min 32 chars). Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `1440` | JWT TTL in minutes (24 h) |
| `DATABASE_URL` | ✅ | — | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | ✅ | — | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | ✅ | — | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | ✅ | — | `redis://redis:6379/2` |
| `SIGNING_KEY_PATH` | | `/app/keys/ed25519_private.pem` | Ed25519 private key path (auto-generated on first start if missing) |
| `SMTP_HOST` | | `""` | SMTP host (leave blank to disable email alerts) |
| `SMTP_PORT` | | `587` | SMTP port |
| `SMTP_USER` | | `""` | SMTP username |
| `SMTP_PASSWORD` | | `""` | SMTP password |
| `SMTP_FROM` | | `noreply@fairguard.local` | From address for alert emails |
| `CORS_ORIGINS` | | `["http://localhost:3000"]` | JSON array of allowed CORS origins |
| `FIRST_ADMIN_EMAIL` | | `admin@fairguard.local` | Seed admin email (created on first startup) |
| `FIRST_ADMIN_PASSWORD` | | `changeme` | Seed admin password — **change immediately** |

Frontend variable (in `frontend/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Backend API base URL for the SPA |

### Installation Steps

#### Option A — Docker Compose (recommended)

```bash
# 1. Clone
git clone https://github.com/wahidpatel05/fairguard.git
cd fairguard

# 2. Configure
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY

# 3. Start all services (builds images, runs migrations, starts backend + frontend)
docker compose up -d --build

# 4. Open dashboard
# http://localhost   (Nginx on port 80)
# http://localhost:8000/api/v1/docs  (Swagger UI)
```

Default admin credentials: `admin@fairguard.local` / `changeme123`  
**Change the password immediately after first login.**

#### Option B — Local Development (no Docker for app code)

```bash
# Start only infrastructure
docker compose up -d postgres redis

# --- Backend ---
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: change DATABASE_URL host from "postgres" → "localhost"
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# --- Frontend (new terminal) ---
cd frontend
npm install
# Confirm frontend/.env: VITE_API_URL=http://localhost:8000/api/v1
npm run dev   # → http://localhost:5173
```

### Alembic Migration Commands

```bash
# Apply all pending migrations (run after pull or first setup)
alembic upgrade head          # locally
docker compose exec backend alembic upgrade head  # via Docker

# Other useful commands
alembic current               # show current revision
alembic history               # full migration history
alembic upgrade +1            # apply next single migration
alembic downgrade -1          # roll back last migration
alembic revision --autogenerate -m "description"  # generate new migration
```

---

## 4. Core Logic & Workflows

### Offline Audit Pipeline

```
Client (CLI / SDK / Dashboard)
  │
  ▼
POST /api/v1/audit/offline  (multipart: CSV file + form fields)
  │
  ├─ 1. Verify project ownership / admin role
  ├─ 2. Load active FairnessContract (is_current=True) → 404 if none
  ├─ 3. Read CSV bytes, compute SHA-256 hash
  ├─ 4. Parse CSV with pandas.read_csv()
  ├─ 5. Validate required columns present, row count ≥ 10
  │
  ├─ 6. FairnessEngine.compute_metrics(df, target_col, prediction_col, sensitive_cols)
  │     ├─ Build MetricFrame (fairlearn) per sensitive column
  │     ├─ Compute: selection_rate, true_positive_rate, false_positive_rate, accuracy
  │     ├─ Derive: disparate_impact, tpr_difference, fpr_difference, accuracy_difference
  │     └─ Return: { global: {...}, by_attribute: { col: { per_group, overall, ... } } }
  │
  ├─ 7. FairnessEngine.evaluate_contracts(metrics, contracts_json)
  │     └─ Evaluate each rule against flat metric values → list of ContractEvaluationResult
  │
  ├─ 8. FairnessEngine.compute_verdict(contract_results)
  │     └─ "pass" | "fail" | "pass_with_warnings"
  │
  ├─ 9. FairnessEngine.generate_mitigation_recommendations(failing_results)
  │
  ├─ 10. Persist OfflineAudit record to DB
  │
  ├─ 11. ReceiptService.create_receipt(...)
  │      ├─ Build canonical payload (audit_id, project_id, dataset_hash, verdict, timestamp, metrics_fingerprint)
  │      ├─ Sign with Ed25519 private key (PyNaCl)
  │      └─ Persist FairnessReceipt to DB
  │
  └─ 12. Return 201 AuditResultResponse (audit + evaluations + recommendations + receipt_id)
```

### Runtime Monitoring Pipeline

```
Model application (SDK / direct API call)
  │
  ▼
POST /api/v1/runtime/ingest  { project_id, decisions: [...] }
  │
  ├─ Validate + persist RuntimeDecision rows to DB
  └─ Trigger recompute_all_snapshots (async via Celery or inline)
        │
        ├─ For each window (last_100, last_1000, last_1hr, last_24hr):
        │   ├─ Query RuntimeDecision rows with window filter
        │   ├─ Expand sensitive_attributes JSONB → individual columns
        │   ├─ FairnessEngine.compute_metrics(df, ...)
        │   ├─ FairnessEngine.evaluate_contracts(metrics, active_contract)
        │   └─ Determine status: healthy | warning | critical
        └─ Upsert RuntimeSnapshot rows (UNIQUE on project/key/window)

GET /api/v1/runtime/status?project_id=...
  └─ get_current_status()
        ├─ Load snapshots from DB
        ├─ If any snapshot > 5 min old → recompute_all_snapshots()
        └─ Return { overall_status, windows: { last_100: {...}, ... } }
```

### Authentication Flow

```
Login → POST /auth/login → JWT (HS256, default 24h TTL) stored in Redis not blacklisted
  │
Every request → get_current_user_either()
  ├─ Try Bearer JWT first (checks Redis blacklist, decodes, looks up User)
  └─ Fall back to X-API-Key header (bcrypt verify against all active APIKey rows)

Logout → POST /auth/logout → adds JWT to Redis blacklist with remaining TTL
```

### Fairness Metrics Reference

| Metric | Measured As | Acceptable Range |
|--------|------------|-----------------|
| **Disparate Impact** | `min(selection_rate) / max(selection_rate)` | ≥ 0.8 (80% rule) |
| **TPR Difference** | `max(TPR) − min(TPR)` across groups | ≤ threshold (e.g. 0.10) |
| **FPR Difference** | `max(FPR) − min(FPR)` across groups | ≤ threshold |
| **Accuracy Difference** | `max(accuracy) − min(accuracy)` across groups | ≤ threshold |

Contract rules specify `metric`, `sensitive_column`, `operator` (`lte`/`gte`), `threshold`, and `severity` (`warn`/`block`). The overall verdict is:
- `"fail"` — any `block`-severity rule failed.
- `"pass_with_warnings"` — only `warn`-severity rules failed.
- `"pass"` — all rules passed.

### Ed25519 Receipt Signing

1. A canonical JSON payload is constructed: `{ audit_id, project_id, dataset_hash, contract_version, verdict, timestamp, metrics_fingerprint }`.
2. Keys are sorted recursively; whitespace removed for deterministic bytes.
3. The signing key is loaded from `SIGNING_KEY_PATH` (32-byte raw Ed25519 private key). If the file doesn't exist, a new keypair is generated and persisted on first startup.
4. The payload bytes are signed with PyNaCl `SigningKey.sign()`.
5. `signed_payload`, `signature`, and `public_key` are all base64url-encoded and stored in `fairness_receipts`.
6. Verification re-decodes all three and calls `VerifyKey.verify(message, signature)`.

### DB Session Lifecycle

```python
# app/core/database.py — get_db() is an async context manager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

All route handlers receive a committed-or-rolled-back session automatically. Always use `await db.flush()` after `db.add(obj)` if you need the object's generated ID before the final commit.

### Celery Task Queue

Celery uses Redis as both broker (`CELERY_BROKER_URL`) and result backend (`CELERY_RESULT_BACKEND`). The worker process is started separately with:

```bash
celery -A app.celery_app worker --loglevel=info --concurrency=4
```

Tasks are registered in `backend/app/tasks/`. Long-running fairness computations should be dispatched as Celery tasks rather than computed inline in API handlers.

---

## 5. Common Issues & Solutions

### Port Already In Use

**Error:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Fix:** Either stop the conflicting process or change the host-side port in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"   # map container port 8000 to host port 8001
```

---

### Backend Cannot Connect to Database

**Symptom:** `asyncpg.exceptions.ConnectionDoesNotExistError` or backend crashes on startup.

**Checks:**
1. Verify `DATABASE_URL` in `.env`:
   - Docker Compose: hostname must be `postgres` (the service name).
   - Local dev: hostname must be `localhost`.
2. Confirm Postgres is healthy: `docker compose ps` and `docker compose logs postgres`.
3. Ensure `postgres` service has passed its health check before the backend starts (handled by `depends_on: condition: service_healthy`).

---

### `alembic upgrade head` Fails — "relation already exists"

**Cause:** The database has tables but no Alembic revision stamp.

**Fix:**
```bash
docker compose exec backend alembic current   # shows no revision
docker compose exec backend alembic stamp head  # stamp as already at head
```

---

### Frontend Shows "Network Error" / Cannot Reach API

1. Confirm `VITE_API_URL` in `frontend/.env` points to the correct backend.
2. Verify the backend is healthy: `curl http://localhost:8000/health`
3. When running Vite dev server locally, the frontend URL is `http://localhost:5173`, **not** `http://localhost:3000`.
4. Check CORS: `CORS_ORIGINS` in `.env` must include the frontend origin.

---

### Reset Admin Password

Update `FIRST_ADMIN_PASSWORD` in `.env`, then recreate the backend container:
```bash
docker compose rm -sf backend
docker compose up -d backend
```

---

### Receipt Signing Key Lost / Rotated

If the Ed25519 private key file at `SIGNING_KEY_PATH` is deleted or replaced:
- New audits will sign with the new key.
- Old receipts can no longer be verified with the new key (the stored `public_key` in `fairness_receipts` will be mismatched).
- To verify old receipts, restore the original key file or implement key rotation by storing key ID metadata.

---

### Celery Worker Not Processing Tasks

1. Confirm `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` match the Redis URLs.
2. Check the worker logs: `docker compose logs celery-worker`.
3. Restart: `docker compose restart celery-worker`.

---

### Performance Considerations

- **Large CSV files**: The audit endpoint reads the entire file into memory. For production use, consider chunked processing or moving computation to a Celery task.
- **API key lookup**: Each request using X-API-Key fetches all active API keys and iterates via bcrypt compare, which is O(n × bcrypt_cost). For high traffic, consider caching hashed keys in Redis.
- **Runtime snapshot staleness**: Snapshots are recomputed when any window is > 5 minutes old. For high-ingestion projects, consider triggering recomputation via Celery task instead of inline on every status request.
- **DB connection pool**: Configured by SQLAlchemy async engine defaults. Tune `pool_size` and `max_overflow` in `database.py` for high-concurrency deployments.

---

## 6. Code Conventions & Standards

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python files | `snake_case` | `fairness.py`, `api_keys.py` |
| Python classes | `PascalCase` | `FairnessEngine`, `ReceiptService` |
| Python functions/variables | `snake_case` | `compute_metrics`, `project_id` |
| SQLAlchemy table names | `snake_case` (plural) | `offline_audits`, `runtime_snapshots` |
| Pydantic schema classes | `PascalCase` with `Out`/`In`/`Create`/`Update` suffix | `AuditOut`, `UserCreate` |
| FastAPI routers | `router` (module-level variable) | `router = APIRouter(prefix="/audit", tags=["audits"])` |
| React components | `PascalCase` | `VerdictBadge`, `MetricCard` |
| TypeScript files | `camelCase` or `PascalCase` | `apiClient.ts`, `AuditPage.tsx` |
| Environment variables | `SCREAMING_SNAKE_CASE` | `SECRET_KEY`, `DATABASE_URL` |

### Code Style

- **Python**: All backend code uses Python 3.11 type hints. `from __future__ import annotations` is used in all model files to allow forward references.
- **Imports**: Circular imports between models are resolved with `TYPE_CHECKING` guards:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from app.models.project import Project
  ```
- **SQLAlchemy ORM**: Use `Mapped[T]` and `mapped_column()` style (SQLAlchemy 2.0). All PKs are UUID with `server_default=text("gen_random_uuid()")`.
- **Async**: All DB operations use `await` with `AsyncSession`. Do not use synchronous SQLAlchemy APIs.
- **FastAPI dependencies**: Auth and DB session are always injected via `Depends(...)`. Never instantiate sessions manually in route handlers.
- **Error responses**: Return `HTTPException(status_code=..., detail="Human-readable message")`. All errors are `{ "detail": "..." }`.
- **TypeScript**: Strict mode enabled. Use `interface` for object shapes and `type` for unions.

### Comment and Documentation Standards

- Docstrings on all service methods and complex functions (Google-style).
- Module-level docstrings where the file has a non-obvious purpose (e.g., `"""Ed25519 receipt signing service using PyNaCl."""`).
- Inline comments only for non-obvious logic (e.g., `# avoid circular import`).
- `# noqa: E712` comments are acceptable alongside SQLAlchemy boolean comparisons (e.g., `FairnessContract.is_current == True`).

### Testing Approach

- The project uses pytest. Tests are expected in `backend/tests/` (or alongside source files).
- Use `httpx.AsyncClient` with `ASGITransport` for async FastAPI route testing.
- Use `pytest-asyncio` for async test functions.
- Fixture scope: use `session`-scoped DB fixtures for performance, `function`-scoped for isolation.
- Mock `ReceiptService` in audit tests to avoid Ed25519 key-file dependencies.

---

## 7. Development Guidelines

### Adding a New Feature

1. **Define the data model** — Add or modify an ORM model in `backend/app/models/`. Ensure you import it in `backend/alembic/env.py` so migrations detect it.
2. **Generate a migration** — `alembic revision --autogenerate -m "add_my_table"`. Review the generated file in `alembic/versions/` before applying.
3. **Add Pydantic schemas** — Create request/response schemas in `backend/app/schemas/`.
4. **Implement service logic** — Add business logic to `backend/app/services/`. Keep route handlers thin — they should only validate input, call services, and return responses.
5. **Add route handlers** — Create a new router file in `backend/app/api/v1/` or add to an existing one. Register it in `backend/app/api/v1/router.py`.
6. **Add frontend support** — Add API client calls in `frontend/src/api/`, define types in `frontend/src/types/`, and create/update pages and components.
7. **Update CLI/SDK if needed** — New audit or runtime endpoints should be exposed in `cli/src/` and `sdk/src/`.

### Modifying Existing Functionality

- **Changing a DB column**: Always use Alembic migrations — never modify tables manually.
- **Changing a fairness metric**: Update `FairnessEngine.compute_metrics()` in `app/services/fairness.py`. Ensure the output keys match what `evaluate_contracts()` and the frontend chart components expect.
- **Changing auth**: `get_current_user_either()` in `app/core/security.py` is the single auth dependency — changes here affect all protected endpoints.
- **Changing the contract schema**: The `contracts_json` JSONB field is schemaless. The `evaluate_contracts()` service reads `contracts_json["rules"]`. Validate the shape at the API layer in the contracts router.

### Deployment Process

```bash
# Build and push Docker images (production)
docker build -f docker/backend/Dockerfile -t fairguard-backend:latest ./backend
docker build -f docker/frontend/Dockerfile -t fairguard-frontend:latest ./frontend

# On the production host:
docker compose pull
docker compose up -d --no-build   # or with --build if building on host
docker compose exec backend alembic upgrade head   # always run migrations
```

Key production checklist:
- Generate a strong `SECRET_KEY` (min 32 chars).
- Back up the Ed25519 signing key at `SIGNING_KEY_PATH` — losing it means old receipts cannot be verified.
- Change `FIRST_ADMIN_PASSWORD` before first startup.
- Restrict `CORS_ORIGINS` to your actual frontend domain.
- Enable SMTP for alert emails or configure a webhook.

### Version Control Practices

- Branch naming: `feature/<description>`, `fix/<description>`, `chore/<description>`.
- All database-schema changes require a corresponding Alembic migration committed in the same branch.
- Do not commit `.env` or the Ed25519 private key (`*.pem`) — both are in `.gitignore`.
- Tag releases with semantic versioning: `v1.2.3`.

---

## 8. Agent-Specific Instructions

### Context Needed for AI Assistance

When asking an AI agent to work on this codebase, provide the following context as needed:

- **Dual backend structure**: There are two overlapping backend packages — `backend/main.py` (legacy models/core) and `backend/app/*` (current active code). All new work should go in `backend/app/*`. Alembic uses `app.*` models. The Docker entrypoint runs `uvicorn main:app` which re-exports from `app.main`.
- **Async everywhere**: All database operations are async. Never use synchronous SQLAlchemy queries in the API or service layer.
- **SQLAlchemy Base split**: `app.core.base` exports `Base` (side-effect free). `app.core.database` re-exports `Base` but importing it also instantiates the engine and settings. Prefer importing `Base` from `app.core.base` in model files.
- **Auth dual-mode**: Endpoints accept both JWT Bearer tokens and `X-API-Key` headers via `get_current_user_either()`.
- **Contract JSONB schema**: `fairness_contracts.contracts_json` is a free-form JSONB blob. The service layer reads `contracts_json["rules"]` where each rule has `id`, `sensitive_column`, `metric`, `operator`, `threshold`, `severity`.

### Areas Requiring Human Approval

- **Alembic migrations**: Auto-generated migrations should be reviewed by a human before applying to production. Destructive changes (DROP COLUMN, type changes) need special care.
- **Security changes**: Any modification to `app/core/security.py`, the JWT configuration, the API key generation/verification logic, or the Ed25519 signing service requires human review.
- **CORS and auth middleware**: Changes to allowed origins or authentication flow must be reviewed.
- **Ed25519 key management**: Never auto-generate code that rotates or replaces the signing key without explicit human instruction.
- **Dependency updates**: Pinned versions in `requirements.txt` and `package.json` should only be changed intentionally.

### Critical Sections to Be Careful With

| Section | Risk | Caution |
|---------|------|---------|
| `app/core/security.py` | Auth bypass | Any change here affects all protected endpoints |
| `app/services/receipt.py` | Receipt integrity | Changing signing logic invalidates existing receipts |
| `alembic/versions/` | Data loss | Destructive migrations are irreversible on production |
| `app/services/fairness.py` | Metric correctness | Changes alter fairness verdicts for all future audits |
| `docker-compose.yml` volume mounts | Key loss | The `./backend/keys` volume mount persists the Ed25519 key |
| `app/core/config.py` | Config drift | Adding a required field without a default will break existing `.env` files |

### Quick Reference for Common Tasks

**Run a fairness audit via CLI:**
```bash
fairguard init --api-url http://localhost:8000/api/v1 --api-key fg_... --no-interactive
fairguard test --data predictions.csv --project-id <id> --target label --prediction score --sensitive gender,age
# Exit 0 = pass, 1 = pass_with_warnings, 2 = fail
```

**Create a project + contract via curl:**
```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fairguard.local","password":"changeme123"}' | jq -r .access_token)

# 2. Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Model","domain":"lending","description":"Test"}'

# 3. Create contract (replace PROJECT_ID)
curl -X POST http://localhost:8000/api/v1/contracts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"PROJECT_ID","contracts_json":{"rules":[{"id":"r1","sensitive_column":"gender","metric":"tpr_difference","operator":"lte","threshold":0.1,"severity":"block"}]}}'
```

**Apply Alembic migrations:**
```bash
docker compose exec backend alembic upgrade head
```

**Check runtime snapshot status:**
```bash
curl "http://localhost:8000/api/v1/runtime/status?project_id=<id>" \
  -H "Authorization: Bearer $TOKEN"
```

**Verify a receipt:**
```bash
curl -X POST "http://localhost:8000/api/v1/receipts/<receipt_id>/verify" \
  -H "Authorization: Bearer $TOKEN"
```

**View backend logs:**
```bash
docker compose logs -f backend
docker compose logs -f celery-worker
```

**Full reset (remove all data):**
```bash
docker compose down -v     # removes postgres_data and redis_data volumes
docker compose up -d --build
```
