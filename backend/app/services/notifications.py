"""Notification service: dispatches fairness alerts via configured channels."""
from __future__ import annotations

import logging
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationConfig, NotificationLog

logger = logging.getLogger(__name__)


class NotificationService:
    """Send notifications to configured channels for a project."""

    @staticmethod
    async def send_notification(
        db: AsyncSession,
        project_id: UUID,
        event_type: str,
        context: dict,
    ) -> None:
        """Dispatch a notification to all active channels for the project.

        Logs each attempt to notification_logs regardless of success.
        """
        result = await db.execute(
            select(NotificationConfig).where(
                NotificationConfig.project_id == project_id,
                NotificationConfig.is_active.is_(True),
            )
        )
        configs = result.scalars().all()

        if not configs:
            logger.debug(
                "No active notification configs for project %s", project_id
            )
            return

        payload = {
            "project_id": str(project_id),
            "event_type": event_type,
            "context": context,
        }

        for config in configs:
            success = False
            error_message: str | None = None

            try:
                if config.channel == "webhook":
                    await NotificationService._send_webhook(config.target, payload)
                    success = True
                elif config.channel == "email":
                    await NotificationService._send_email(config.target, event_type, payload)
                    success = True
                else:
                    logger.warning("Unknown notification channel: %s", config.channel)
                    error_message = f"Unknown channel: {config.channel}"
            except Exception as exc:
                error_message = str(exc)
                logger.error(
                    "Failed to send %s notification to %s for project %s: %s",
                    config.channel,
                    config.target,
                    project_id,
                    exc,
                )

            log_entry = NotificationLog(
                project_id=project_id,
                trigger_event=event_type,
                payload_json=payload,
                success=success,
                error_message=error_message,
            )
            db.add(log_entry)

        await db.commit()

    @staticmethod
    async def _send_webhook(url: str, payload: dict) -> None:
        """POST payload as JSON to the webhook URL."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

    @staticmethod
    async def _send_email(
        to_address: str, subject: str, payload: dict
    ) -> None:
        """Send a plain-text email alert.

        Falls back to a no-op log if SMTP is not configured.
        """
        from app.core.config import settings

        if not settings.SMTP_HOST:
            logger.info(
                "SMTP not configured; skipping email to %s (event=%s)",
                to_address,
                subject,
            )
            return

        import smtplib
        from email.mime.text import MIMEText

        body = (
            f"FairGuard Alert\n\n"
            f"Event: {payload.get('event_type')}\n"
            f"Project: {payload.get('project_id')}\n\n"
            f"Context:\n{payload.get('context')}\n"
        )

        msg = MIMEText(body)
        msg["Subject"] = f"[FairGuard] {subject}"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_address

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.SMTP_FROM, [to_address], msg.as_string())
