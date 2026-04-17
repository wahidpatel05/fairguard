"""Pydantic schemas for receipt endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReceiptOut(BaseModel):
    """Full receipt response schema."""

    id: UUID
    audit_id: UUID
    project_id: UUID
    dataset_hash: str | None
    contract_version: int | None
    contracts_summary: Any | None
    metrics_summary: Any | None
    verdict: str | None
    signed_payload: str | None
    signature: str | None
    public_key: str | None
    onchain_tx_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerifyReceiptResponse(BaseModel):
    """Response for receipt signature verification."""

    valid: bool
    receipt_id: str
    verified_at: str
    reason: str | None = None
