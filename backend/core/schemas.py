"""Pydantic schemas for request/response validation."""
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed = {"admin", "project_owner", "viewer"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class APIKeyCreate(BaseModel):
    name: str
    project_id: Optional[uuid.UUID] = None


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    project_id: Optional[uuid.UUID]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(APIKeyResponse):
    raw_key: str  # returned only once at creation


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: str = "other"

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        allowed = {"hiring", "lending", "healthcare", "other"}
        if v not in allowed:
            raise ValueError(f"domain must be one of {allowed}")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    owner_id: uuid.UUID
    domain: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Contracts ─────────────────────────────────────────────────────────────────

VALID_METRIC_TYPES = {
    "disparate_impact",
    "tpr_gap",
    "fpr_gap",
    "accuracy_gap",
    "tpr_difference",
}


class ContractRule(BaseModel):
    metric: str
    threshold: float
    operator: str = "gte"  # gte = metric value must be >= threshold; lte = <=

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v):
        if v not in VALID_METRIC_TYPES:
            raise ValueError(f"metric must be one of {VALID_METRIC_TYPES}")
        return v

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError("threshold must be numeric")
        return float(v)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v):
        if v not in {"gte", "lte"}:
            raise ValueError("operator must be 'gte' or 'lte'")
        return v


class ContractCreate(BaseModel):
    version: str
    rules: list[ContractRule]
    description: Optional[str] = None


class ContractResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    version: str
    contract_json: dict
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


# ── Audits ────────────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    project_id: uuid.UUID
    target_column: str
    prediction_column: str
    sensitive_columns: str  # comma-separated
    endpoint_id: Optional[str] = None


class ContractStatus(BaseModel):
    contract_id: str
    metric: str
    value: float
    threshold: float
    operator: str
    status: str  # pass / fail / warn
    explanation: str


class AuditResponse(BaseModel):
    audit_log_id: uuid.UUID
    receipt_id: uuid.UUID
    project_id: uuid.UUID
    dataset_hash: str
    metrics: dict
    contract_statuses: list[ContractStatus]
    verdict: str
    timestamp: datetime


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    contract_version: Optional[str]
    dataset_hash: str
    metrics_json: dict
    verdict: str
    timestamp: datetime
    endpoint_id: Optional[str]

    model_config = {"from_attributes": True}


# ── Runtime ───────────────────────────────────────────────────────────────────

class DecisionItem(BaseModel):
    decision_id: str
    endpoint_id: str
    sensitive_attributes: dict
    decision_outcome: bool
    ground_truth: Optional[bool] = None
    timestamp: Optional[datetime] = None


class RuntimeIngestRequest(BaseModel):
    project_id: uuid.UUID
    decisions: list[DecisionItem]


class RuntimeIngestResponse(BaseModel):
    ingested: int
    project_id: uuid.UUID


class RuntimeStatusResponse(BaseModel):
    project_id: uuid.UUID
    endpoint_id: str
    window: str
    metrics: dict
    status: str
    computed_at: datetime


class RuntimeMetricsHistory(BaseModel):
    project_id: uuid.UUID
    endpoint_id: str
    window: str
    history: list[dict]


# ── Receipts ──────────────────────────────────────────────────────────────────

class ReceiptResponse(BaseModel):
    id: uuid.UUID
    audit_log_id: uuid.UUID
    project_id: uuid.UUID
    endpoint_id: Optional[str]
    dataset_hash: str
    contract_version: Optional[str]
    contracts_list: dict
    metrics_summary: dict
    verdict: str
    signature: str   # base64
    public_key: str  # base64
    timestamp: datetime

    model_config = {"from_attributes": True}


class ReceiptVerifyResponse(BaseModel):
    valid: bool
    receipt_id: uuid.UUID
    details: str


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertConfigCreate(BaseModel):
    channel_type: str
    config_json: dict

    @field_validator("channel_type")
    @classmethod
    def validate_channel(cls, v):
        if v not in {"email", "webhook"}:
            raise ValueError("channel_type must be 'email' or 'webhook'")
        return v


class AlertConfigResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    channel_type: str
    config_json: dict
    is_active: bool

    model_config = {"from_attributes": True}
