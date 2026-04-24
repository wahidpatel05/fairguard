"""FairGuard API – FastAPI application entry point.

Delegates to app.main which uses ORM models aligned with the Alembic
migration schema.  The legacy core.* / models.db modules are no longer
wired here to avoid ProgrammingError caused by column/table mismatches.
"""
from app.main import app  # noqa: F401 – re-exported for `uvicorn main:app`
