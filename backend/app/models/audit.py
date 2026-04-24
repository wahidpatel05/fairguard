from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class OfflineAudit(Base):
    __tablename__ = "offline_audits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    contract_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fairness_contracts.id"), nullable=True
    )
    dataset_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dataset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prediction_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sensitive_columns: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verdict: Mapped[str | None] = mapped_column(
        Enum("pass", "fail", "pass_with_warnings", name="audit_verdict"),
        nullable=True,
    )
    triggered_by: Mapped[str | None] = mapped_column(
        Enum("api", "cli", name="audit_trigger"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="offline_audits")
    contract_version: Mapped["FairnessContract | None"] = relationship(
        "FairnessContract", back_populates="offline_audits"
    )
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])
    receipt: Mapped["FairnessReceipt | None"] = relationship(
        "FairnessReceipt", back_populates="audit", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<OfflineAudit id={self.id} project_id={self.project_id}"
            f" verdict={self.verdict!r}>"
        )


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.contract import FairnessContract
    from app.models.project import Project
    from app.models.receipt import FairnessReceipt
    from app.models.user import User
