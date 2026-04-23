from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import httpx


class FairGuardAPIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class APIClient:
    """Thin httpx wrapper that attaches Bearer auth and raises on errors."""

    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout: float = 120.0) -> None:
        self.base_url = api_url.rstrip("/")
        headers = {"Accept": "application/json"}
        if api_key:
            # Prefer X-API-Key header; the backend also accepts Bearer tokens.
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise FairGuardAPIError(response.status_code, detail)

    def get(self, path: str, **kwargs: Any) -> Any:
        response = self._client.get(path, **kwargs)
        self._raise_for_status(response)
        return response.json()

    def get_bytes(self, path: str, **kwargs: Any) -> bytes:
        """Download a binary resource and return the raw bytes."""
        response = self._client.get(path, **kwargs)
        self._raise_for_status(response)
        return response.content

    def post(self, path: str, **kwargs: Any) -> Any:
        response = self._client.post(path, **kwargs)
        self._raise_for_status(response)
        return response.json()

    def post_file(self, path: str, file_path: Path, extra_fields: dict[str, str] | None = None) -> Any:
        with file_path.open("rb") as fh:
            files = {"file": (file_path.name, fh, "text/csv")}
            data = extra_fields or {}
            response = self._client.post(path, files=files, data=data)
        self._raise_for_status(response)
        return response.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
