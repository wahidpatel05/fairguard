from __future__ import annotations

from celery import Celery

from app.core.config import settings

app = Celery("fairguard")

app.config_from_object(
    {
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,
        "task_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
    }
)

app.autodiscover_tasks(
    [
        "app.tasks.audit_tasks",
        "app.tasks.runtime_tasks",
        "app.tasks.notification_tasks",
    ]
)
