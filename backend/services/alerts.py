"""Notification and alert service for FairGuard."""
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class AlertService:
    """Dispatches alerts to configured channels (email/webhook)."""

    async def send_alert(self, project_id: str, alert_type: str, payload: dict, configs: list[dict]) -> None:
        """Send an alert to all active configured channels for this project."""
        for config in configs:
            channel = config.get("channel_type")
            cfg = config.get("config_json", {})
            if channel == "email":
                await self._send_email_alert(project_id, alert_type, payload, cfg)
            elif channel == "webhook":
                await self._send_webhook_alert(project_id, alert_type, payload, cfg)

    async def _send_email_alert(self, project_id: str, alert_type: str, payload: dict, config: dict) -> None:
        """Log email alert (production would integrate with SMTP/SendGrid)."""
        recipient = config.get("recipient", "unknown")
        logger.warning(
            "[ALERT EMAIL] project=%s type=%s recipient=%s payload=%s",
            project_id, alert_type, recipient, payload,
        )

    async def _send_webhook_alert(self, project_id: str, alert_type: str, payload: dict, config: dict) -> None:
        """POST alert payload to a webhook URL."""
        url = config.get("url")
        if not url:
            logger.error("[ALERT WEBHOOK] No URL configured for project %s", project_id)
            return
        body = {"project_id": project_id, "alert_type": alert_type, **payload}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=body)
                resp.raise_for_status()
                logger.info("[ALERT WEBHOOK] Delivered to %s (status %s)", url, resp.status_code)
        except Exception as exc:
            logger.error("[ALERT WEBHOOK] Failed to deliver to %s: %s", url, exc)

    async def check_and_alert(
        self,
        project_id: str,
        previous_status: Optional[str],
        new_status: str,
        details: dict,
        configs: list[dict],
    ) -> None:
        """Send an alert only when status transitions to a worse state."""
        status_rank = {"healthy": 0, "warning": 1, "critical": 2}
        prev_rank = status_rank.get(previous_status or "healthy", 0)
        new_rank = status_rank.get(new_status, 0)
        if new_rank > prev_rank:
            alert_type = f"status_degraded_to_{new_status}"
            await self.send_alert(project_id, alert_type, details, configs)


alert_service = AlertService()
