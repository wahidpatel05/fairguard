from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(
        Enum("email", "webhook", name="notification_channel"),
        nullable=False,
    )
    target: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="notification_configs"
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationConfig id={self.id} project_id={self.project_id}"
            f" channel={self.channel!r}>"
        )


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    trigger_event: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sent_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="notification_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog id={self.id} project_id={self.project_id}"
            f" success={self.success}>"
        )


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.project import Project
