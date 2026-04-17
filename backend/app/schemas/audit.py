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


class AuditSummary(BaseModel):
    """Lightweight audit summary for list views."""

    id: UUID
    project_id: UUID
    dataset_filename: str | None
    dataset_hash: str | None
    verdict: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContractEvaluationResult(BaseModel):
    """Result of evaluating a single fairness contract rule."""

    contract_id: str
    attribute: str | None = None
    metric: str
    value: float | None = None
    threshold: float
    operator: str
    passed: bool
    severity: str | None = None
    explanation: str


class AuditResultResponse(BaseModel):
    """Full audit result including contract evaluations and recommendations."""

    audit: AuditOut
    contract_evaluations: list[ContractEvaluationResult]
    recommendations: list[dict[str, Any]]
    receipt_id: UUID | None = None
