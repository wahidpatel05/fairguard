from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, get_redis
from app.models.api_key import APIKey
from app.models.user import User

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
_oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def password_hash(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# API key helpers
# ---------------------------------------------------------------------------

def generate_api_key() -> tuple[str, str]:
    """Return (plaintext_key, bcrypt_hash)."""
    plaintext = "fg_" + secrets.token_urlsafe(32)
    hashed = _pwd_context.hash(plaintext)
    return plaintext, hashed


def verify_api_key(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# FastAPI auth dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check Redis blacklist
    blacklisted = await redis.get(f"blacklist:{token}")
    if blacklisted:
        raise credentials_exc

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exc

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc

    return user


async def _resolve_api_key_user(
    x_api_key: str,
    db: AsyncSession,
) -> User | None:
    """Look up the User associated with a plaintext API key header."""
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)  # noqa: E712
    )
    api_keys = result.scalars().all()

    matched_key: APIKey | None = None
    for key in api_keys:
        if verify_api_key(x_api_key, key.key_hash):
            matched_key = key
            break

    if matched_key is None:
        return None

    matched_key.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    user_result = await db.execute(
        select(User).where(User.id == matched_key.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user_api_key(
    x_api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if x_api_key is None:
        return None
    return await _resolve_api_key_user(x_api_key, db)


async def get_current_user_either(
    token: str | None = Depends(_oauth2_scheme_optional),
    x_api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    # Try JWT first
    if token is not None:
        blacklisted = await redis.get(f"blacklist:{token}")
        if not blacklisted:
            payload = decode_access_token(token)
            if payload is not None:
                user_id: str | None = payload.get("sub")
                if user_id is not None:
                    result = await db.execute(
                        select(User).where(User.id == user_id)
                    )
                    user = result.scalar_one_or_none()
                    if user is not None and user.is_active:
                        return user

    # Fall back to API key
    if x_api_key is not None:
        user = await _resolve_api_key_user(x_api_key, db)
        if user is not None:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
