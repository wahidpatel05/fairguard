"""Application configuration using pydantic-settings."""
import base64
from typing import Optional
from pydantic_settings import BaseSettings
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption


def _generate_default_keypair():
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return (
        base64.b64encode(private_bytes).decode(),
        base64.b64encode(public_bytes).decode(),
    )


_default_private, _default_public = _generate_default_keypair()


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fairguard"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "changeme-secret-key-32-bytes-long!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SIGNING_PRIVATE_KEY: str = _default_private
    SIGNING_PUBLIC_KEY: str = _default_public

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
