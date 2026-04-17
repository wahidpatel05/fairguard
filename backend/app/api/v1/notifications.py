"""API endpoints for notification configuration and testing."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_project_access, require_project_owner_or_admin
from app.core.security import get_current_user_either
from app.models.notification import NotificationConfig, NotificationLog
from app.models.project import Project
from app.models.user import User
from app.schemas.notification import (
    NotificationConfigCreate,
    NotificationConfigOut,
    NotificationLogOut,
    TestNotificationResponse,
)
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# POST /notifications/config  – create a notification config
# ---------------------------------------------------------------------------


@router.post(
    "/config",
    response_model=NotificationConfigOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification_config(
    payload: NotificationConfigCreate,
    current_user: User = Depends(require_project_owner_or_admin),
    db: AsyncSession = Depends(get_db),
) -> NotificationConfigOut:
    """Create a new email or webhook notification config for a project."""
    # Verify the caller has access to the owning project
    proj_result = await db.execute(
        select(Project).where(Project.id == payload.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this project is forbidden",
        )

    config = NotificationConfig(
        project_id=payload.project_id,
        channel=payload.channel,
        target=payload.target,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return NotificationConfigOut.model_validate(config)


# ---------------------------------------------------------------------------
# GET /notifications/config  – list configs for a project
# ---------------------------------------------------------------------------


@router.get("/config", response_model=list[NotificationConfigOut])
async def list_notification_configs(
    project_id: UUID,
    _project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationConfigOut]:
    """List all notification configs for a project."""
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.project_id == project_id
        )
    )
    configs = result.scalars().all()
    return [NotificationConfigOut.model_validate(c) for c in configs]


# ---------------------------------------------------------------------------
# DELETE /notifications/config/{config_id}  – hard-delete a config
# ---------------------------------------------------------------------------


@router.delete("/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_config(
    config_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a notification config after verifying project access."""
    result = await db.execute(
        select(NotificationConfig).where(NotificationConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification config not found",
        )

    # Verify the caller has access to the owning project
    proj_result = await db.execute(
        select(Project).where(Project.id == config.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this project is forbidden",
        )

    await db.delete(config)
    await db.flush()


# ---------------------------------------------------------------------------
# POST /notifications/test/{config_id}  – send a test notification
# ---------------------------------------------------------------------------


@router.post("/test/{config_id}", response_model=TestNotificationResponse)
async def test_notification(
    config_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> TestNotificationResponse:
    """Send a test notification through the specified config."""
    result = await db.execute(
        select(NotificationConfig).where(NotificationConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification config not found",
        )

    # Verify project access
    proj_result = await db.execute(
        select(Project).where(Project.id == config.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this project is forbidden",
        )

    project_name = project.name
    base_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else ""
    dashboard_url = f"{base_url}/projects/{config.project_id}"

    test_context: dict = {
        "audit_id": "test-audit-id",
        "verdict": "fail",
        "contracts_violated": [
            {
                "contract_id": "test",
                "attribute": "gender",
                "metric": "disparate_impact",
                "value": 0.65,
                "threshold": 0.80,
            }
        ],
        "metrics": {"test": True},
        "dashboard_url": dashboard_url,
    }

    success = False
    error: str | None = None
    payload_json: dict = {}

    try:
        if config.channel == "email":
            subject, html_body, text_body = NotificationService.build_email_body(
                "test_notification", project_name, test_context
            )
            payload_json = {"subject": subject, "event_type": "test_notification"}
            success, error = await NotificationService.send_email(
                config.target, subject, html_body, text_body
            )
        elif config.channel == "webhook":
            wh_payload = NotificationService.build_webhook_payload(
                str(config.project_id),
                project_name,
                "test_notification",
                test_context,
            )
            payload_json = wh_payload
            success, error = await NotificationService.send_webhook(
                config.target, wh_payload
            )
    except Exception as exc:  # noqa: BLE001
        success = False
        error = str(exc)
        logger.warning(
            "Test notification failed for config_id=%s: %s", config_id, exc
        )

    # Log the test attempt (never log target address/URL)
    log_entry = NotificationLog(
        project_id=config.project_id,
        trigger_event="test_notification",
        payload_json=payload_json,
        success=success,
        error_message=error,
    )
    db.add(log_entry)
    await db.flush()

    message = "Test notification sent successfully" if success else f"Test failed: {error}"
    return TestNotificationResponse(
        success=success,
        message=message,
        config_id=config_id,
    )


# ---------------------------------------------------------------------------
# GET /notifications/logs  – list notification logs for a project
# ---------------------------------------------------------------------------


@router.get("/logs", response_model=list[NotificationLogOut])
async def list_notification_logs(
    project_id: UUID,
    _project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationLogOut]:
    """Return notification logs for a project, newest first (max 200)."""
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.project_id == project_id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(200)
    )
    logs = result.scalars().all()
    return [NotificationLogOut.model_validate(log) for log in logs]
