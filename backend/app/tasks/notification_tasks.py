"""Celery tasks for async notification dispatch."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from app.celery_app import app as celery_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db_context():
    """Async context manager that provides a DB session."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@celery_app.task(bind=True, max_retries=3)
def send_notification_task(
    self,
    project_id: str,
    event_type: str,
    context: dict,
) -> None:
    """Sync Celery wrapper around the async notification service.

    Retries up to 3 times with exponential back-off (2^attempt seconds).
    """
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            _send_notification_async(project_id, event_type, context)
        )
    except Exception as exc:
        logger.exception(
            "send_notification_task failed for project %s event %s: %s",
            project_id,
            event_type,
            exc,
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        loop.close()


async def _send_notification_async(
    project_id: str,
    event_type: str,
    context: dict,
) -> None:
    """Open a DB session and dispatch the notification."""
    from app.services.notifications import NotificationService

    async with get_db_context() as db:
        await NotificationService.send_notification(
            db, UUID(project_id), event_type, context
        )
