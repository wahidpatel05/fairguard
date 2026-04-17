"""Type definitions for the FairGuard Python SDK."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AuditResult:
    """Result of an offline fairness audit."""

    audit_id: str
    project_id: str
    verdict: str
    dataset_hash: str
    contract_evaluations: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    receipt_id: Optional[str] = None


@dataclass
class RuntimeStatus:
    """Current runtime fairness monitoring status for a project."""

    project_id: str
    overall_status: str
    windows: dict[str, dict[str, Any]]
    aggregation_key: Optional[str] = None


@dataclass
class Receipt:
    """A cryptographically signed fairness audit receipt."""

    id: str
    audit_id: str
    verdict: str
    signature: Optional[str]
    public_key: Optional[str]
    created_at: str


@dataclass
class VerificationResult:
    """Result of verifying a fairness receipt's cryptographic signature."""

    valid: bool
    receipt_id: str
    verified_at: str
    reason: Optional[str] = None
