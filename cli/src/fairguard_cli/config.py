from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


CONFIG_FILE = ".fairguard.yml"


class FairGuardConfig(BaseModel):
    api_url: str = Field(default="https://api.fairguard.io")
    project_id: Optional[str] = None
    api_key: Optional[str] = None


def _find_config_file() -> Optional[Path]:
    """Walk up from cwd looking for .fairguard.yml."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILE
        if candidate.exists():
            return candidate
    return None


def load_config() -> FairGuardConfig:
    """Load config from .fairguard.yml then override with env vars."""
    data: dict = {}

    config_path = _find_config_file()
    if config_path:
        with config_path.open() as fh:
            loaded = yaml.safe_load(fh) or {}
        data.update(loaded)

    # Environment variables always win.
    if api_url := os.getenv("FAIRGUARD_API_URL"):
        data["api_url"] = api_url
    if api_key := os.getenv("FAIRGUARD_API_KEY"):
        data["api_key"] = api_key
    if project_id := os.getenv("FAIRGUARD_PROJECT_ID"):
        data["project_id"] = project_id

    return FairGuardConfig(**data)


def write_config(config: FairGuardConfig, path: Path = Path(CONFIG_FILE)) -> None:
    """Persist config to .fairguard.yml (never writes api_key to disk)."""
    payload = {
        "api_url": config.api_url,
        "project_id": config.project_id,
    }
    with path.open("w") as fh:
        yaml.dump(payload, fh, default_flow_style=False)
