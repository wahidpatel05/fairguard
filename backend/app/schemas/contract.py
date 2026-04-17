"""Pydantic schemas for FairnessContract."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractRule(BaseModel):
    """A single fairness contract rule."""

    id: str
    metric: str
    threshold: float
    operator: str = Field(default="gte", pattern="^(gte|lte)$")
    sensitive_column: str | None = None
    description: str | None = None


class ContractCreate(BaseModel):
    """Payload for creating a new contract version."""

    contracts: list[ContractRule]
    notes: str | None = None


class ContractOut(BaseModel):
    """Response schema for a fairness contract."""

    id: UUID
    project_id: UUID
    version: int
    is_current: bool
    contracts_json: dict[str, Any]
    created_by: UUID
    created_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
