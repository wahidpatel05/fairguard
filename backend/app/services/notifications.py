"""Notification service: email (SMTP) and webhook dispatch."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

import aiosmtplib
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import NotificationConfig, NotificationLog
from app.models.project import Project

logger = logging.getLogger(__name__)


class NotificationService:
    """Send fairness-alert notifications via email or webhook."""

    # ------------------------------------------------------------------
    # Low-level transports
    # ------------------------------------------------------------------

    @staticmethod
    async def send_email(
        to_address: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> tuple[bool, str | None]:
        """Send an HTML/text email via SMTP STARTTLS.

        Returns (True, None) on success or (False, error_str) on failure.
        SMTP connection failures are caught and returned – never raised.
        """
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured – skipping email send")
            return False, "SMTP not configured"

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM
        message["To"] = to_address
        message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                start_tls=True,
            ) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(message)
            return True, None
        except aiosmtplib.SMTPException as exc:
            return False, str(exc)
        except ConnectionRefusedError as exc:
            return False, str(exc)
        except asyncio.TimeoutError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001 – catch-all safety net
            return False, str(exc)

    @staticmethod
    async def send_webhook(
        url: str,
        payload: dict,
        max_retries: int = 3,
    ) -> tuple[bool, str | None]:
        """POST *payload* as JSON to *url* with exponential-backoff retries.

        Returns (True, None) on 2xx or (False, reason_str) otherwise.
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "FairGuard/1.0",
        }
        last_error: str = "No attempts made"
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.is_success:
                        return True, None
                    last_error = f"HTTP {response.status_code}"
                except httpx.HTTPError as exc:
                    last_error = str(exc)

                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return False, last_error

    # ------------------------------------------------------------------
    # Message builders
    # ------------------------------------------------------------------

    @staticmethod
    def build_email_body(
        event_type: str,
        project_name: str,
        context: dict,
    ) -> tuple[str, str, str]:
        """Return (subject, html_body, text_body) for a FairGuard alert."""
        subject = f"FairGuard Alert: {event_type} for project {project_name}"

        is_critical = "critical" in event_type or "failed" in event_type
        is_warning = "warning" in event_type
        if is_critical:
            severity_colour = "#c0392b"
            severity_label = "CRITICAL / FAIL"
        elif is_warning:
            severity_colour = "#e67e22"
            severity_label = "WARNING"
        else:
            severity_colour = "#2980b9"
            severity_label = "INFO"

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        dashboard_url = context.get("dashboard_url", "#")
        contracts_violated: list[dict] = context.get("contracts_violated", [])

        rows_html = ""
        rows_text = ""

        if event_type == "offline_audit_failed_block" and contracts_violated:
            rows_html += (
                "<h3 style='margin:16px 0 8px;'>Violated Contracts</h3>"
                "<table style='border-collapse:collapse;width:100%;font-size:13px;'>"
                "<thead><tr style='background:#f2f2f2;'>"
                "<th style='border:1px solid #ccc;padding:6px;text-align:left;'>Contract ID</th>"
                "<th style='border:1px solid #ccc;padding:6px;text-align:left;'>Attribute</th>"
                "<th style='border:1px solid #ccc;padding:6px;text-align:left;'>Metric</th>"
                "<th style='border:1px solid #ccc;padding:6px;text-align:right;'>Value</th>"
                "<th style='border:1px solid #ccc;padding:6px;text-align:right;'>Threshold</th>"
                "</tr></thead><tbody>"
            )
            rows_text += "\nViolated Contracts:\n"
            for c in contracts_violated:
                rows_html += (
                    "<tr>"
                    f"<td style='border:1px solid #ccc;padding:6px;'>{c.get('contract_id', '')}</td>"
                    f"<td style='border:1px solid #ccc;padding:6px;'>{c.get('attribute', '')}</td>"
                    f"<td style='border:1px solid #ccc;padding:6px;'>{c.get('metric', '')}</td>"
                    f"<td style='border:1px solid #ccc;padding:6px;text-align:right;'>{c.get('value', '')}</td>"
                    f"<td style='border:1px solid #ccc;padding:6px;text-align:right;'>{c.get('threshold', '')}</td>"
                    "</tr>"
                )
                rows_text += (
                    f"  - {c.get('contract_id', '')} | {c.get('attribute', '')} | "
                    f"{c.get('metric', '')} = {c.get('value', '')} "
                    f"(threshold {c.get('threshold', '')})\n"
                )
            rows_html += "</tbody></table>"

        elif event_type in ("runtime_status_warning", "runtime_status_critical"):
            window = context.get("window", {})
            status_val = context.get("status", "")
            rows_html += (
                "<h3 style='margin:16px 0 8px;'>Runtime Status Details</h3>"
                "<table style='border-collapse:collapse;width:100%;font-size:13px;'>"
                "<thead><tr style='background:#f2f2f2;'>"
                "<th style='border:1px solid #ccc;padding:6px;text-align:left;'>Field</th>"
                "<th style='border:1px solid #ccc;padding:6px;text-align:left;'>Value</th>"
                "</tr></thead><tbody>"
                f"<tr><td style='border:1px solid #ccc;padding:6px;'>Status</td>"
                f"<td style='border:1px solid #ccc;padding:6px;'>{status_val}</td></tr>"
                f"<tr><td style='border:1px solid #ccc;padding:6px;'>Window</td>"
                f"<td style='border:1px solid #ccc;padding:6px;'>{window}</td></tr>"
                "</tbody></table>"
            )
            rows_text += f"\nStatus: {status_val}\nWindow: {window}\n"
            if contracts_violated:
                rows_html += (
                    "<h3 style='margin:16px 0 8px;'>Failing Contracts</h3>"
                    "<table style='border-collapse:collapse;width:100%;font-size:13px;'>"
                    "<thead><tr style='background:#f2f2f2;'>"
                    "<th style='border:1px solid #ccc;padding:6px;text-align:left;'>Contract ID</th>"
                    "<th style='border:1px solid #ccc;padding:6px;text-align:left;'>Metric</th>"
                    "<th style='border:1px solid #ccc;padding:6px;text-align:right;'>Value</th>"
                    "<th style='border:1px solid #ccc;padding:6px;text-align:right;'>Threshold</th>"
                    "</tr></thead><tbody>"
                )
                rows_text += "\nFailing Contracts:\n"
                for c in contracts_violated:
                    rows_html += (
                        "<tr>"
                        f"<td style='border:1px solid #ccc;padding:6px;'>{c.get('contract_id', '')}</td>"
                        f"<td style='border:1px solid #ccc;padding:6px;'>{c.get('metric', '')}</td>"
                        f"<td style='border:1px solid #ccc;padding:6px;text-align:right;'>{c.get('value', '')}</td>"
                        f"<td style='border:1px solid #ccc;padding:6px;text-align:right;'>{c.get('threshold', '')}</td>"
                        "</tr>"
                    )
                    rows_text += (
                        f"  - {c.get('contract_id', '')} | {c.get('metric', '')} = "
                        f"{c.get('value', '')} (threshold {c.get('threshold', '')})\n"
                    )
                rows_html += "</tbody></table>"

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f4f4f4;padding:24px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <tr>
            <td style="background:{severity_colour};padding:24px 32px;">
              <h1 style="margin:0;color:#ffffff;font-size:20px;">
                FairGuard Notification
              </h1>
              <p style="margin:4px 0 0;color:#ffffff;opacity:0.9;font-size:14px;">
                {severity_label} &mdash; {event_type}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px;color:#333333;">
              <p style="margin:0 0 8px;"><strong>Project:</strong> {project_name}</p>
              <p style="margin:0 0 16px;"><strong>Timestamp:</strong> {timestamp}</p>
              {rows_html}
              <p style="margin:24px 0 0;">
                <a href="{dashboard_url}"
                   style="background:{severity_colour};color:#ffffff;
                          padding:10px 20px;border-radius:4px;
                          text-decoration:none;font-size:14px;
                          display:inline-block;">
                  View in Dashboard
                </a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#f8f8f8;padding:16px 32px;
                       border-top:1px solid #eeeeee;
                       font-size:12px;color:#999999;">
              This is an automated alert from FairGuard. Do not reply.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

        text_body = (
            f"FairGuard Alert: {event_type}\n"
            f"Severity: {severity_label}\n"
            f"Project: {project_name}\n"
            f"Timestamp: {timestamp}\n"
            f"{rows_text}\n"
            f"Dashboard: {dashboard_url}\n\n"
            "This is an automated alert from FairGuard. Do not reply."
        )

        return subject, html_body, text_body

    @staticmethod
    def build_webhook_payload(
        project_id: str,
        project_name: str,
        event: str,
        context: dict,
    ) -> dict:
        """Return a standardised webhook payload dict."""
        if "critical" in event or "failed" in event:
            severity = "critical"
        elif "warning" in event:
            severity = "warning"
        else:
            severity = "info"

        return {
            "source": "fairguard",
            "version": "1.0",
            "project_id": project_id,
            "project_name": project_name,
            "event": event,
            "severity": severity,
            "contracts_violated": context.get("contracts_violated", []),
            "metric_values": context.get("metric_values", {}),
            "dashboard_url": context.get("dashboard_url", ""),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    # ------------------------------------------------------------------
    # Main dispatcher
    # ------------------------------------------------------------------

    @staticmethod
    async def send_notification(
        db: AsyncSession,
        project_id: UUID,
        event_type: str,
        context: dict,
    ) -> list[dict]:
        """Dispatch notifications for *event_type* to all active configs.

        Returns a list of result dicts: {channel, target, success, error}.
        Failures are logged but never raised to the caller.
        """
        results: list[dict] = []

        try:
            # 1. Fetch project name
            proj_result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = proj_result.scalar_one_or_none()
            project_name = project.name if project else str(project_id)

            # 2. Fetch active notification configs
            configs_result = await db.execute(
                select(NotificationConfig).where(
                    NotificationConfig.project_id == project_id,
                    NotificationConfig.is_active == True,  # noqa: E712
                )
            )
            configs: list[NotificationConfig] = list(configs_result.scalars().all())

            # 3. Dispatch per config
            for config in configs:
                success = False
                error: str | None = None
                payload_json: dict = {}

                try:
                    if config.channel == "email":
                        subject, html_body, text_body = (
                            NotificationService.build_email_body(
                                event_type, project_name, context
                            )
                        )
                        payload_json = {"subject": subject, "event_type": event_type}
                        success, error = await NotificationService.send_email(
                            config.target, subject, html_body, text_body
                        )
                    elif config.channel == "webhook":
                        wh_payload = NotificationService.build_webhook_payload(
                            str(project_id), project_name, event_type, context
                        )
                        payload_json = wh_payload
                        success, error = await NotificationService.send_webhook(
                            config.target, wh_payload
                        )
                    else:
                        error = f"Unknown channel: {config.channel}"
                except Exception as exc:  # noqa: BLE001
                    error = str(exc)
                    success = False

                if not success:
                    # Log config_id only – never log target address/URL
                    logger.warning(
                        "Notification failed for config_id=%s: %s",
                        config.id,
                        error,
                    )

                # 4. Persist log entry
                log_entry = NotificationLog(
                    project_id=project_id,
                    trigger_event=event_type,
                    payload_json=payload_json,
                    success=success,
                    error_message=error,
                )
                db.add(log_entry)

                results.append(
                    {
                        "channel": config.channel,
                        "target": config.target,
                        "success": success,
                        "error": error,
                    }
                )

            await db.flush()

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "send_notification failed for project_id=%s event=%s: %s",
                project_id,
                event_type,
                exc,
            )

        return results
