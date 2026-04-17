"""Pydantic schemas for OfflineAudit."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    """Response schema for an offline audit."""

    id: UUID
    project_id: UUID
    contract_version_id: UUID | None
    dataset_filename: str | None
    dataset_hash: str | None
    target_column: str | None
    prediction_column: str | None
    sensitive_columns: list[str] | None
    metrics_json: dict[str, Any] | None
    verdict: str | None
    triggered_by: str | None
    user_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
