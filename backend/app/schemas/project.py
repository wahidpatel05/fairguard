from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    domain: Literal["hiring", "lending", "healthcare", "other"]


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    domain: Literal["hiring", "lending", "healthcare", "other"] | None = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    domain: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
