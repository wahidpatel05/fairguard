from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class FairnessContract(Base):
    __tablename__ = "fairness_contracts"
    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_contract_project_version"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    contracts_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="contracts")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    offline_audits: Mapped[list["OfflineAudit"]] = relationship(
        "OfflineAudit", back_populates="contract_version", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<FairnessContract id={self.id} project_id={self.project_id}"
            f" version={self.version} is_current={self.is_current}>"
        )


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.audit import OfflineAudit
    from app.models.project import Project
    from app.models.user import User
