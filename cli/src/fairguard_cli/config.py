from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


# Global config at ~/.fairguard/config.json (written by `fairguard init`)
GLOBAL_CONFIG_PATH = Path.home() / ".fairguard" / "config.json"

# Per-project YAML config (backward-compatible)
YAML_CONFIG_FILE = ".fairguard.yml"


class FairGuardConfig(BaseModel):
    api_url: str = Field(default="http://localhost:8000/api/v1")
    project_id: Optional[str] = None
    api_key: Optional[str] = None


def _find_yaml_config() -> Optional[Path]:
    """Walk up from cwd looking for .fairguard.yml."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / YAML_CONFIG_FILE
        if candidate.exists():
            return candidate
    return None


def load_config() -> FairGuardConfig:
    """Load config from sources in priority order (highest wins):
    1. Environment variables
    2. Per-project .fairguard.yml
    3. Global ~/.fairguard/config.json
    """
    data: dict = {}

    # 3. Global config (lowest priority among file-based)
    if GLOBAL_CONFIG_PATH.exists():
        try:
            global_cfg = json.loads(GLOBAL_CONFIG_PATH.read_text())
            data.update(global_cfg)
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Per-project YAML overrides global
    yaml_path = _find_yaml_config()
    if yaml_path:
        try:
            with yaml_path.open() as fh:
                loaded = yaml.safe_load(fh) or {}
            data.update(loaded)
        except (yaml.YAMLError, OSError):
            pass

    # 1. Environment variables always win
    if api_url := os.getenv("FAIRGUARD_API_URL"):
        data["api_url"] = api_url
    if api_key := os.getenv("FAIRGUARD_API_KEY"):
        data["api_key"] = api_key
    if project_id := os.getenv("FAIRGUARD_PROJECT_ID"):
        data["project_id"] = project_id

    return FairGuardConfig(**data)


def save_global_config(api_url: str, api_key: str) -> None:
    """Persist API URL and key to ~/.fairguard/config.json."""
    GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLOBAL_CONFIG_PATH.write_text(
        json.dumps({"api_url": api_url, "api_key": api_key}, indent=2)
    )
    # Restrict permissions so only the owner can read
    GLOBAL_CONFIG_PATH.chmod(0o600)


def write_config(api_url: str, project_id: Optional[str], path: Path = Path(YAML_CONFIG_FILE)) -> None:
    """Persist api_url and project_id to .fairguard.yml (never writes api_key)."""
    payload: dict = {"api_url": api_url}
    if project_id:
        payload["project_id"] = project_id
    with path.open("w") as fh:
        yaml.dump(payload, fh, default_flow_style=False)

