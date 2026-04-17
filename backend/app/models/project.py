from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    domain: Mapped[str] = mapped_column(
        Enum("hiring", "lending", "healthcare", "other", name="project_domain"),
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    contracts: Mapped[list["FairnessContract"]] = relationship(
        "FairnessContract", back_populates="project", lazy="select"
    )
    offline_audits: Mapped[list["OfflineAudit"]] = relationship(
        "OfflineAudit", back_populates="project", lazy="select"
    )
    receipts: Mapped[list["FairnessReceipt"]] = relationship(
        "FairnessReceipt", back_populates="project", lazy="select"
    )
    runtime_decisions: Mapped[list["RuntimeDecision"]] = relationship(
        "RuntimeDecision", back_populates="project", lazy="select"
    )
    runtime_snapshots: Mapped[list["RuntimeSnapshot"]] = relationship(
        "RuntimeSnapshot", back_populates="project", lazy="select"
    )
    notification_configs: Mapped[list["NotificationConfig"]] = relationship(
        "NotificationConfig", back_populates="project", lazy="select"
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="project", lazy="select"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="project", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r} domain={self.domain!r}>"


# Avoid undefined name warnings for type checkers – resolved by SQLAlchemy registry
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.api_key import APIKey
    from app.models.audit import OfflineAudit
    from app.models.contract import FairnessContract
    from app.models.notification import NotificationConfig, NotificationLog
    from app.models.receipt import FairnessReceipt
    from app.models.runtime import RuntimeDecision, RuntimeSnapshot
    from app.models.user import User
