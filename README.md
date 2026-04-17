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

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Passlib, Asyncpg
- **AI/Fairness**: Fairlearn, Numpy, Pandas, Scikit-learn
- **Database Architecture**: PostgreSQL 15, Redis 7 (Caching)
- **Frontend SPA**: React 19, TypeScript, Vite 8, Tailwind CSS, Recharts, React Query, React Hook Form
- **Security & Encyption**: JWT (HS256), bcrypt, Ed25519 (for signing receipts)

---

## Installation & Quick Start

FairGuard is fully multi-container Dockerized for easy deployments.

### Prerequisites

- Node.js 22.x+ (if modifying frontend locally)
- Python 3.11+
- Docker & Docker Compose

### 1. Environment Configuration

Create a `.env` file in the root `fairguard/` folder:

```bash
# fairguard/.env

SECRET_KEY="generate-a-secure-32-byte-string"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES="1440"
DATABASE_URL="postgresql+asyncpg://fairguard:fairguard@postgres:5432/fairguard"
REDIS_URL="redis://redis:6379/0"
```

Also, create one `frontend/.env` file:
```bash
# fairguard/frontend/.env

VITE_API_URL="http://localhost:8000/api/v1"
```

### 2. Spinning up the Containers

Build and run the Docker infrastructure from the root workspace:

```bash
docker-compose up -d --build
```

### 3. Initialize the Database

Apply the initial required SQLAlchemy Alembic database migrations:
```bash
docker-compose exec backend alembic upgrade head
```

---

## Access the Platform!

Once everything boots and the database is configured, go to:
- **Frontend UI / Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: `http://localhost:8000/api/v1`
- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Example Local/CI CLI Workflow

To test the CLI locally, you can install the standalone package:
```bash
pip install fairguard-cli
```

Provide the tool with your generated API key (created from inside the Web App Dashboard):
```bash
fairguard init
fairguard test --data predictions.csv --target actual_label --prediction model_score --sensitive gender,race

# Check runtime status
fairguard status --project-id <your-ui-project-id>
```

---

## Project Architecture

```
fairguard/
├── backend/          # FastAPI App (Python)
│   ├── api/v1/       # Route handlers (auth, audits, contracts, projects, receipts, runtime)
│   ├── core/         # Pydantic Schemas, Global configurations, DB & security singletons
│   ├── models/       # SQLAlchemy PostgreSQL ORM schemas
│   └── services/     # Deep business & logic isolation (Crypto signing, metric calculations)
├── frontend/         # Vite React SPA (TypeScript)
│   └── src/
│       ├── api/      # Axios request handlers
│       ├── components/ # Granular reusable Tailwind parts (Charts, TrafficLight)
│       └── pages/    # Main routing container layouts (Audits, Dashboard)
├── cli/              # PyPi Pip package (Built with Typer framework)
├── sdk/              # Client API Wrapper (for AI pipeline runtime integration)
├── docker/           # Specific Dockerfiles + nginx proxy configuration
└── docs/             # Granular doc collections
```
- **Container**: Docker, Docker Compose, Kubernetes-compatible

## License

Apache 2.0