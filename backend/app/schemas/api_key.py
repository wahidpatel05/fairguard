from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ApiKeyCreate(BaseModel):
    name: str
    project_id: UUID | None = None


class ApiKeyOut(BaseModel):
    id: UUID
    name: str
    project_id: UUID | None
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreated(BaseModel):
    id: UUID
    name: str
    key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
