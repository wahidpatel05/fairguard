"""SQLAlchemy ORM models for FairGuard."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, JSON, LargeBinary, Enum as SAEnum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


def _now() -> datetime:
    return datetime.now()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(SAEnum("admin", "project_owner", "viewer", name="user_role"), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="owner")
    api_keys: Mapped[list["APIKey"]] = relationship("APIKey", back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    domain: Mapped[str] = mapped_column(SAEnum("hiring", "lending", "healthcare", "other", name="project_domain"), default="other")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    contracts: Mapped[list["FairnessContract"]] = relationship("FairnessContract", back_populates="project")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="project")
    runtime_decisions: Mapped[list["RuntimeDecision"]] = relationship("RuntimeDecision", back_populates="project")
    runtime_metrics: Mapped[list["RuntimeMetrics"]] = relationship("RuntimeMetrics", back_populates="project")
    alert_configs: Mapped[list["AlertConfig"]] = relationship("AlertConfig", back_populates="project")
    receipts: Mapped[list["FairnessReceipt"]] = relationship("FairnessReceipt", back_populates="project")
    api_keys: Mapped[list["APIKey"]] = relationship("APIKey", back_populates="project")


class FairnessContract(Base):
    __tablename__ = "fairness_contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    project: Mapped["Project"] = relationship("Project", back_populates="contracts")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="contract")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    contract_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("fairness_contracts.id"), nullable=True)
    contract_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    verdict: Mapped[str] = mapped_column(SAEnum("pass", "fail", "pass_with_warnings", name="audit_verdict"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)
    endpoint_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="audit_logs")
    user: Mapped["User"] = relationship("User")
    contract: Mapped[Optional["FairnessContract"]] = relationship("FairnessContract", back_populates="audit_logs")
    receipt: Mapped[Optional["FairnessReceipt"]] = relationship("FairnessReceipt", back_populates="audit_log", uselist=False)


class FairnessReceipt(Base):
    __tablename__ = "fairness_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    endpoint_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contracts_list: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics_summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    signature: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)

    audit_log: Mapped["AuditLog"] = relationship("AuditLog", back_populates="receipt")
    project: Mapped["Project"] = relationship("Project", back_populates="receipts")


class RuntimeDecision(Base):
    __tablename__ = "runtime_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    endpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sensitive_attributes: Mapped[dict] = mapped_column(JSON, nullable=False)
    decision_outcome: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ground_truth: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    project: Mapped["Project"] = relationship("Project", back_populates="runtime_decisions")


class RuntimeMetrics(Base):
    __tablename__ = "runtime_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    endpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    window_type: Mapped[str] = mapped_column(SAEnum("1hr", "24hr", "rolling_n", name="window_type"), nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(SAEnum("healthy", "warning", "critical", name="runtime_status"), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    project: Mapped["Project"] = relationship("Project", back_populates="runtime_metrics")


class AlertConfig(Base):
    __tablename__ = "alert_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    channel_type: Mapped[str] = mapped_column(SAEnum("email", "webhook", name="channel_type"), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    project: Mapped["Project"] = relationship("Project", back_populates="alert_configs")


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="api_keys")
