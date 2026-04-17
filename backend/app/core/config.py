from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_URL: str  # e.g. postgresql+asyncpg://user:pass@host:5432/db

    # Redis / Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Ed25519 signing key (PEM file path)
    SIGNING_KEY_PATH: str = "/app/keys/ed25519_private.pem"

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@fairguard.local"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # First admin seed
    FIRST_ADMIN_EMAIL: str = "admin@fairguard.local"
    FIRST_ADMIN_PASSWORD: str = "changeme"


settings = Settings()
