# FairGuard — Run Guide

This guide walks you through every way to run FairGuard: using Docker Compose (recommended), running the backend and frontend individually for local development, and using the CLI / Python SDK.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Environment Configuration](#3-environment-configuration)
4. [Running with Docker Compose (Recommended)](#4-running-with-docker-compose-recommended)
5. [Running Locally Without Docker](#5-running-locally-without-docker)
   - [5a. Backend (FastAPI)](#5a-backend-fastapi)
   - [5b. Frontend (React / Vite)](#5b-frontend-react--vite)
6. [Database Migrations](#6-database-migrations)
7. [Accessing the Platform](#7-accessing-the-platform)
8. [Using the CLI](#8-using-the-cli)
9. [Using the Python SDK](#9-using-the-python-sdk)
10. [Stopping & Cleaning Up](#10-stopping--cleaning-up)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| **Docker** | 24.x+ | Container runtime |
| **Docker Compose** | v2.x (`docker compose`) | Multi-container orchestration |
| **Python** | 3.11+ | Local backend / CLI development |
| **Node.js** | 22.x+ | Local frontend development |
| **npm** | 10.x+ | Frontend package management |

> **Only Docker + Docker Compose are required** if you use the Docker Compose workflow. Python and Node.js are only needed for local development without containers.

---

## 2. Clone the Repository

```bash
git clone https://github.com/wahidpatel05/fairguard.git
cd fairguard
```

---

## 3. Environment Configuration

### 3a. Root `.env` (used by Docker Compose and the backend)

Copy the provided example and fill in the required values:

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```dotenv
# Generate a secure key with:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-long-random-secret-key

ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Used by Docker Compose — leave as-is when running via docker-compose
DATABASE_URL=postgresql+asyncpg://fairguard:fairguard@postgres:5432/fairguard
REDIS_URL=redis://redis:6379/0

# Optional: SMTP for email notifications (leave SMTP_HOST blank to disable)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

# Allowed frontend origins (JSON array)
CORS_ORIGINS=["http://localhost:3000"]

# Bootstrap admin account created on first startup
FIRST_ADMIN_EMAIL=admin@fairguard.local
FIRST_ADMIN_PASSWORD=changeme
```

### 3b. Frontend `.env`

```bash
# fairguard/frontend/.env  (already present in the repo)
VITE_API_URL=http://localhost:8000/api/v1
```

> The frontend `.env` file is already included. Only update `VITE_API_URL` if your backend is hosted at a different address.

---

## 4. Running with Docker Compose (Recommended)

This single command builds and starts **PostgreSQL 15**, **Redis 7**, the **FastAPI backend** (port `8000`), and the **React frontend** (port `3000`):

```bash
docker compose up -d --build
```

### Apply database migrations

Run Alembic migrations inside the backend container to initialise the schema:

```bash
docker compose exec backend alembic upgrade head
```

That's it — FairGuard is now running. See [Section 7](#7-accessing-the-platform) for the URLs.

### Viewing logs

```bash
# All services
docker compose logs -f

# Single service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

---

## 5. Running Locally Without Docker

Use this approach when you want to iterate quickly on the backend or frontend without rebuilding Docker images.

You still need a running **PostgreSQL 15** and **Redis 7** instance. The quickest way is to spin up only those two services via Docker Compose:

```bash
docker compose up -d postgres redis
```

### 5a. Backend (FastAPI)

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure the backend environment file
cp .env.example .env
# Edit .env — change DATABASE_URL host from "postgres" to "localhost":
#   DATABASE_URL=postgresql+asyncpg://fairguard:fairguard@localhost:5432/fairguard
#   REDIS_URL=redis://localhost:6379/0

# 4. Apply database migrations
alembic upgrade head

# 5. Start the development server (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`.

### 5b. Frontend (React / Vite)

Open a **new terminal**:

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Confirm the API URL in frontend/.env
#    VITE_API_URL=http://localhost:8000/api/v1

# 3. Start the Vite development server (hot-reload)
npm run dev
```

The frontend will be available at `http://localhost:5173` (Vite default).

---

## 6. Database Migrations

FairGuard uses **Alembic** to manage database schema migrations.

| Command | Description |
|---|---|
| `alembic upgrade head` | Apply all pending migrations (run after first setup or pulling new code) |
| `alembic upgrade +1` | Apply the next single migration |
| `alembic downgrade -1` | Roll back the last migration |
| `alembic current` | Show the current migration revision |
| `alembic history` | Show full migration history |

**Via Docker Compose:**

```bash
docker compose exec backend alembic upgrade head
```

**Locally (inside `backend/` with venv activated):**

```bash
alembic upgrade head
```

---

## 7. Accessing the Platform

Once all services are running and migrations are applied:

| Service | URL |
|---|---|
| **Frontend Dashboard** | http://localhost:3000 |
| **Backend REST API** | http://localhost:8000/api/v1 |
| **Interactive API Docs (Swagger)** | http://localhost:8000/docs |
| **ReDoc API Reference** | http://localhost:8000/redoc |
| **Health Check Endpoint** | http://localhost:8000/health |

### Default admin credentials

The first admin account is created automatically on startup using the values from your `.env`:

```
Email:    admin@fairguard.local   (FIRST_ADMIN_EMAIL)
Password: changeme                (FIRST_ADMIN_PASSWORD)
```

> **Change the default password immediately after first login.**

---

## 8. Using the CLI

The `fairguard-cli` package integrates FairGuard into CI/CD pipelines.

### Install

```bash
pip install fairguard-cli
```

### Configure

```bash
# Interactive setup — saves api_url and project_id to .fairguard.yml
fairguard init

# Export your API key as an environment variable (never written to disk)
export FAIRGUARD_API_KEY=fgk_...
```

### Common commands

```bash
# Run an offline fairness audit against a CSV file
fairguard test \
  --data predictions.csv \
  --target actual_label \
  --prediction model_score \
  --sensitive gender,race

# Generate a Markdown report of the latest audit
fairguard report --output report.md

# Check live runtime monitoring status
fairguard status --project-id <your-project-id>
```

Exit code `0` = audit passed; exit code `1` = audit failed or error (suitable as a CI gate).

---

## 9. Using the Python SDK

The SDK lets you push live AI decision data to FairGuard's runtime firewall from within your ML pipeline.

```bash
pip install -e sdk/   # install from source, or use the published PyPI package
```

```python
from fairguard_sdk import FairGuardClient

client = FairGuardClient(
    api_url="http://localhost:8000/api/v1",
    api_key="fgk_...",
    project_id="proj_abc123",
)

# Push a single decision event
client.log_decision(
    endpoint_id="loan-approval",
    prediction=1,
    ground_truth=1,
    sensitive_attributes={"gender": "female", "age_group": "25-34"},
)
```

---

## 10. Stopping & Cleaning Up

```bash
# Stop all running containers (preserves volumes)
docker compose down

# Stop and remove containers AND the database volume (full reset)
docker compose down -v

# Remove built images as well
docker compose down -v --rmi all
```

---

## 11. Troubleshooting

### Port already in use

```
Error: address already in use 0.0.0.0:8000
```

Another process is using port 8000 or 3000. Either stop that process or change the host port in `docker-compose.yml` (e.g., `"8001:8000"`).

---

### Backend cannot connect to the database

Verify the `DATABASE_URL` in your `.env`:

- **Docker Compose**: hostname must be `postgres` (the service name).
- **Local dev**: hostname must be `localhost` (or wherever your DB is running).

Check that the `postgres` container is healthy:

```bash
docker compose ps
docker compose logs postgres
```

---

### `alembic upgrade head` fails with "relation already exists"

The database may already be partially initialised. Check the current state:

```bash
docker compose exec backend alembic current
```

If no revision is stamped, stamp it and retry:

```bash
docker compose exec backend alembic stamp head
```

---

### Frontend shows "Network Error" / cannot reach the API

Confirm `VITE_API_URL` in `frontend/.env` points to the correct backend address and that the backend container is healthy:

```bash
curl http://localhost:8000/health
```

When running the Vite dev server locally, the frontend is at `http://localhost:5173`, **not** `http://localhost:3000`.

---

### Resetting the admin password

Update `FIRST_ADMIN_PASSWORD` in `.env`, then remove and recreate the backend container:

```bash
docker compose rm -sf backend
docker compose up -d backend
```

---

*For CI/CD integration examples (GitHub Actions, GitLab CI), see [`docs/ci-examples.md`](docs/ci-examples.md).*
