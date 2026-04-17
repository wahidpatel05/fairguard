from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import httpx
from pydantic import BaseModel


class AuditResult(BaseModel):
    audit_id: str
    project_id: str
    verdict: str
    metrics: dict[str, Any] = {}
    violations: list[str] = []
    receipt_id: Optional[str] = None
    created_at: Optional[str] = None


class FairGuardAPIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class FairGuardClient:
    """
    Python SDK client for the FairGuard API.

    Parameters
    ----------
    api_url:
        Base URL of the FairGuard API (e.g. ``https://api.fairguard.io``).
    api_key:
        Bearer token used to authenticate requests.
    timeout:
        Request timeout in seconds (default 60).
    """

    def __init__(self, api_url: str, api_key: str, timeout: float = 60.0) -> None:
        self.api_url = api_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise FairGuardAPIError(response.status_code, detail)

    def _get(self, path: str, **kwargs: Any) -> Any:
        response = self._client.get(path, **kwargs)
        self._raise_for_status(response)
        return response.json()

    def _post(self, path: str, **kwargs: Any) -> Any:
        response = self._client.post(path, **kwargs)
        self._raise_for_status(response)
        return response.json()

    def _post_file(
        self,
        path: str,
        file_path: Path,
        extra_fields: dict[str, str] | None = None,
    ) -> Any:
        with file_path.open("rb") as fh:
            files = {"file": (file_path.name, fh, "text/csv")}
            data = extra_fields or {}
            response = self._client.post(path, files=files, data=data)
        self._raise_for_status(response)
        return response.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_audit_data(
        self,
        project_id: str,
        data_path: str | Path,
        target_column: str,
        prediction_column: str,
        sensitive_columns: list[str],
        endpoint_id: Optional[str] = None,
    ) -> AuditResult:
        """
        Upload a CSV file and trigger an offline fairness audit.

        Parameters
        ----------
        project_id:
            The FairGuard project to audit against.
        data_path:
            Local path to the CSV file containing predictions.
        target_column:
            Name of the ground-truth label column.
        prediction_column:
            Name of the model prediction / score column.
        sensitive_columns:
            List of column names representing sensitive attributes (e.g. ``["gender", "age_group"]``).
        endpoint_id:
            Optional endpoint ID to scope the audit.

        Returns
        -------
        AuditResult
            Structured result including verdict, metrics, and violations.
        """
        file_path = Path(data_path)
        extra: dict[str, str] = {
            "project_id": project_id,
            "target_column": target_column,
            "prediction_column": prediction_column,
            "sensitive_columns": ",".join(sensitive_columns),
        }
        if endpoint_id:
            extra["endpoint_id"] = endpoint_id

        raw = self._post_file("/api/v1/audit/offline", file_path=file_path, extra_fields=extra)
        return AuditResult(project_id=project_id, **raw)

    def get_metrics(
        self,
        project_id: str,
        endpoint_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retrieve the latest fairness metrics for a project.

        Parameters
        ----------
        project_id:
            Target project.
        endpoint_id:
            Optional endpoint to scope the query.

        Returns
        -------
        dict
            Raw metrics payload from the API.
        """
        params: dict[str, str] = {}
        if endpoint_id:
            params["endpoint_id"] = endpoint_id
        return self._get(f"/api/v1/projects/{project_id}/metrics", params=params)

    def get_receipt(self, receipt_id: str) -> dict[str, Any]:
        """
        Fetch a cryptographic audit receipt by ID.

        Parameters
        ----------
        receipt_id:
            The receipt identifier returned by a previous audit.

        Returns
        -------
        dict
            Receipt payload including signature and metadata.
        """
        return self._get(f"/api/v1/receipts/{receipt_id}")

    def verify_receipt(self, receipt_id: str) -> dict[str, Any]:
        """
        Verify the cryptographic integrity of an audit receipt.

        Parameters
        ----------
        receipt_id:
            The receipt identifier to verify.

        Returns
        -------
        dict
            Verification result with ``valid`` boolean and details.
        """
        return self._post(f"/api/v1/receipts/{receipt_id}/verify")

    def get_runtime_status(
        self,
        project_id: str,
        endpoint_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get real-time monitoring status for a project or endpoint.

        Parameters
        ----------
        project_id:
            Target project.
        endpoint_id:
            Optional endpoint to scope the query.

        Returns
        -------
        dict
            Status payload including per-endpoint health and violation counts.
        """
        params: dict[str, str] = {}
        if endpoint_id:
            params["endpoint_id"] = endpoint_id
        return self._get(f"/api/v1/projects/{project_id}/status", params=params)

    def ingest_decisions(
        self,
        project_id: str,
        decisions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Ingest a batch of model decisions for real-time monitoring.

        Each decision dict should contain at minimum the prediction value and
        the relevant sensitive-attribute values.

        Parameters
        ----------
        project_id:
            Target project.
        decisions:
            List of decision records.

        Returns
        -------
        dict
            Ingestion confirmation with a ``receipt_id`` and ``ingested_count``.
        """
        payload = {"project_id": project_id, "decisions": decisions}
        return self._post("/api/v1/decisions/ingest", json=payload)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FairGuardClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_default_client: Optional[FairGuardClient] = None


def _get_default_client() -> FairGuardClient:
    if _default_client is None:
        raise RuntimeError(
            "No default FairGuardClient configured. "
            "Either instantiate FairGuardClient directly or call "
            "fairguard_sdk.configure(api_url=..., api_key=...)."
        )
    return _default_client


def configure(api_url: str, api_key: str) -> None:
    """Configure a module-level default client for convenience functions."""
    global _default_client
    _default_client = FairGuardClient(api_url=api_url, api_key=api_key)


def send_audit_data(
    project_id: str,
    data_path: str | Path,
    target_column: str,
    prediction_column: str,
    sensitive_columns: list[str],
    endpoint_id: Optional[str] = None,
) -> AuditResult:
    """Module-level convenience wrapper around :meth:`FairGuardClient.send_audit_data`."""
    return _get_default_client().send_audit_data(
        project_id=project_id,
        data_path=data_path,
        target_column=target_column,
        prediction_column=prediction_column,
        sensitive_columns=sensitive_columns,
        endpoint_id=endpoint_id,
    )


def get_metrics(
    project_id: str,
    endpoint_id: Optional[str] = None,
) -> dict[str, Any]:
    """Module-level convenience wrapper around :meth:`FairGuardClient.get_metrics`."""
    return _get_default_client().get_metrics(project_id=project_id, endpoint_id=endpoint_id)


def get_receipt(receipt_id: str) -> dict[str, Any]:
    """Module-level convenience wrapper around :meth:`FairGuardClient.get_receipt`."""
    return _get_default_client().get_receipt(receipt_id=receipt_id)
