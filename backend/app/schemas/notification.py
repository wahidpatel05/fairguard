"""Pydantic v2 schemas for Notification resources."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class NotificationConfigCreate(BaseModel):
    """Payload for creating a new notification config."""

    project_id: UUID
    channel: Literal["email", "webhook"]
    target: str

    @model_validator(mode="after")
    def validate_target_for_channel(self) -> "NotificationConfigCreate":
        if self.channel == "email":
            if not _EMAIL_RE.match(self.target):
                raise ValueError(
                    f"target must be a valid email address for channel 'email', "
                    f"got: {self.target!r}"
                )
        elif self.channel == "webhook":
            if not self.target.startswith("http"):
                raise ValueError(
                    "target must start with 'http' for channel 'webhook'"
                )
        return self


class NotificationConfigOut(BaseModel):
    """Response schema for a notification config record."""

    id: UUID
    project_id: UUID
    channel: str
    target: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationLogOut(BaseModel):
    """Response schema for a notification log entry."""

    id: UUID
    project_id: UUID
    trigger_event: str | None
    payload_json: dict[str, Any] | None
    sent_at: datetime
    success: bool | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class TestNotificationResponse(BaseModel):
    """Response after triggering a test notification."""

    success: bool
    message: str
    config_id: UUID
