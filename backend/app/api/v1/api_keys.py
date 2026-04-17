from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import generate_api_key, get_current_user_either
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["api_keys"])


@router.post("/", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    plaintext, key_hash = generate_api_key()
    api_key = APIKey(
        user_id=current_user.id,
        project_id=payload.project_id,
        key_hash=key_hash,
        name=payload.name,
        is_active=True,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key=plaintext,
        created_at=api_key.created_at,
    )


@router.get("/", response_model=list[ApiKeyOut])
async def list_api_keys(
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyOut]:
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    keys = result.scalars().all()
    return [ApiKeyOut.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if current_user.role != "admin" and api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's API key",
        )

    api_key.is_active = False
    await db.flush()
