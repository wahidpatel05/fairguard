"""FairGuard ORM models package.

Importing this package registers all models with the SQLAlchemy metadata so
that Alembic autogenerate and relationship resolution work correctly.
"""
from __future__ import annotations

from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.contract import FairnessContract  # noqa: F401
from app.models.audit import OfflineAudit  # noqa: F401
from app.models.receipt import FairnessReceipt  # noqa: F401
from app.models.runtime import RuntimeDecision, RuntimeSnapshot  # noqa: F401
from app.models.notification import NotificationConfig, NotificationLog  # noqa: F401
from app.models.api_key import APIKey  # noqa: F401

__all__ = [
    "User",
    "Project",
    "FairnessContract",
    "OfflineAudit",
    "FairnessReceipt",
    "RuntimeDecision",
    "RuntimeSnapshot",
    "NotificationConfig",
    "NotificationLog",
    "APIKey",
]
