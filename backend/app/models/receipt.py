from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FairnessReceipt(Base):
    __tablename__ = "fairness_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offline_audits.id"),
        nullable=False,
        unique=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    model_endpoint_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contracts_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signed_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    onchain_tx_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    audit: Mapped["OfflineAudit"] = relationship(
        "OfflineAudit", back_populates="receipt"
    )
    project: Mapped["Project"] = relationship("Project", back_populates="receipts")

    def __repr__(self) -> str:
        return (
            f"<FairnessReceipt id={self.id} audit_id={self.audit_id}"
            f" verdict={self.verdict!r}>"
        )


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.audit import OfflineAudit
    from app.models.project import Project
