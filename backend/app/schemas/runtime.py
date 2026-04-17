"""Pydantic v2 schemas for runtime monitoring endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DecisionItem(BaseModel):
    """A single model decision to ingest."""

    decision_id: str
    sensitive_attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    outcome: str
    ground_truth: str | None = None
    timestamp: datetime


class IngestDecisionsRequest(BaseModel):
    """Request body for POST /runtime/ingest."""

    model_config = ConfigDict(protected_namespaces=())

    project_id: UUID
    model_endpoint_id: str
    aggregation_key: str | None = None
    decisions: list[DecisionItem] = Field(..., min_length=1)


class RuntimeWindowStatus(BaseModel):
    """Status summary for a single time window."""

    metrics: dict
    status: str
    evaluated_at: datetime | None
    count: int


class RuntimeStatusResponse(BaseModel):
    """Response for GET /runtime/status."""

    project_id: str
    aggregation_key: str | None
    windows: dict[str, RuntimeWindowStatus]
    overall_status: str


class SnapshotOut(BaseModel):
    """Serialised RuntimeSnapshot row."""

    id: UUID
    project_id: UUID
    aggregation_key: str | None
    window_type: str
    metrics_json: dict | None
    status: str
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
