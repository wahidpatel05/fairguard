from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RuntimeDecision(Base):
    __tablename__ = "runtime_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    model_endpoint_id: Mapped[str] = mapped_column(Text, nullable=False)
    aggregation_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_id: Mapped[str] = mapped_column(Text, nullable=False)
    sensitive_attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    ground_truth: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="runtime_decisions"
    )

    def __repr__(self) -> str:
        return (
            f"<RuntimeDecision id={self.id} project_id={self.project_id}"
            f" decision_id={self.decision_id!r}>"
        )


class RuntimeSnapshot(Base):
    __tablename__ = "runtime_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "aggregation_key",
            "window_type",
            name="uq_snapshot_project_key_window",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    aggregation_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    window_type: Mapped[str] = mapped_column(
        Enum(
            "last_100",
            "last_1000",
            "last_1hr",
            "last_24hr",
            name="window_type",
        ),
        nullable=False,
    )
    metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("healthy", "warning", "critical", name="snapshot_status"),
        nullable=False,
    )
    evaluated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="runtime_snapshots"
    )

    def __repr__(self) -> str:
        return (
            f"<RuntimeSnapshot id={self.id} project_id={self.project_id}"
            f" window_type={self.window_type!r} status={self.status!r}>"
        )


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.project import Project
