from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_either
from app.models.project import Project
from app.models.user import User


async def require_admin(
    current_user: User = Depends(get_current_user_either),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_project_owner_or_admin(
    current_user: User = Depends(get_current_user_either),
) -> User:
    if current_user.role not in ("admin", "project_owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project owner or admin access required",
        )
    return current_user


async def require_project_access(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_either),
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role == "admin":
        return project

    if project.owner_id == current_user.id:
        return project

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access to this project is forbidden",
    )


async def get_project_or_404(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project
