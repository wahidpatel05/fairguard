"""Celery tasks for async audit report generation."""
from __future__ import annotations

import logging

from app.celery_app import app as celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_report_task(
    self,
    audit_id: str,
    format: str,
    output_path: str | None = None,
) -> None:
    """Async report generation task.

    Not used directly in MVP but available for large datasets.
    Generates a fairness audit report in the requested format.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            _run_generate_report(audit_id, format, output_path)
        )
    except Exception as exc:
        logger.exception(
            "generate_report_task failed for audit %s: %s", audit_id, exc
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        loop.close()


async def _run_generate_report(
    audit_id: str,
    format: str,
    output_path: str | None,
) -> None:
    """Async helper: open DB session and call ReportService."""
    from app.core.database import AsyncSessionLocal
    from app.services.reports import ReportService
    from uuid import UUID

    async with AsyncSessionLocal() as db:
        await ReportService.generate_report(
            db=db,
            audit_id=UUID(audit_id),
            format=format,
            output_path=output_path,
        )
