"""FairGuard API – FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine
from core.database import Base  # noqa: F401 – triggers model registration
import models.db  # noqa: F401 – register all ORM models

from api.v1 import auth, projects, contracts, audits, runtime, receipts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="FairGuard API",
    version="1.0.0",
    description="AI Fairness Firewall & Audit Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(audits.router, prefix="/api/v1")
app.include_router(runtime.router, prefix="/api/v1")
app.include_router(receipts.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
