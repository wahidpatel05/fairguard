"""Celery tasks for async runtime snapshot computation."""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.celery_app import app as celery_app

logger = logging.getLogger(__name__)


def _get_db_context():
    """Return an async context manager that yields a DB session."""
    from app.core.database import AsyncSessionLocal

    return AsyncSessionLocal()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def recompute_snapshots_task(
    self,
    project_id: str,
    aggregation_key: str | None,
) -> dict:
    """Sync Celery wrapper around recompute_all_snapshots.

    1. Creates a new asyncio event loop.
    2. Opens a DB session.
    3. Calls recompute_all_snapshots.
    4. If any window has a critical/warning status, triggers send_notification_task.
    5. On exception, retries with exponential back-off (2^attempt seconds).
    """
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            _run_recompute(project_id, aggregation_key)
        )
    except Exception as exc:
        logger.exception(
            "recompute_snapshots_task failed for project %s: %s", project_id, exc
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        loop.close()

    # Check if any window has an alertable status
    alertable_statuses = {"critical", "warning"}
    for window_type, snapshot in result.items():
        win_status = snapshot.get("status")
        if win_status in alertable_statuses:
            from app.tasks.notification_tasks import send_notification_task

            send_notification_task.delay(
                project_id,
                f"runtime_{win_status}",
                {
                    "window_type": window_type,
                    "status": win_status,
                    "count": snapshot.get("count", 0),
                },
            )
            # Only send one notification per task execution (highest severity)
            if win_status == "critical":
                break

    return result


async def _run_recompute(project_id: str, aggregation_key: str | None) -> dict:
    """Async helper: open DB session and call recompute_all_snapshots."""
    from app.services.runtime import recompute_all_snapshots

    async with _get_db_context() as db:
        return await recompute_all_snapshots(db, UUID(project_id), aggregation_key)
