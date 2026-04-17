from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Optional

import httpx
import pandas as pd
from pydantic import BaseModel

from fairguard_sdk.types import AuditResult, Receipt, RuntimeStatus, VerificationResult


class FairGuardAPIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class FairGuardClient:
    """
    Python SDK client for the FairGuard API.

    Supports both synchronous and asynchronous usage.

    Parameters
    ----------
    api_url:
        Base URL of the FairGuard API (e.g. ``http://localhost:8000/api/v1``).
    api_key:
        API key used to authenticate requests (passed as ``X-API-Key`` header).
    timeout:
        Request timeout in seconds (default 120).
    """

    def __init__(self, api_url: str, api_key: str, timeout: float = 120.0) -> None:
        self.api_url = api_url.rstrip("/")
        _headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
        }
        self._client = httpx.Client(
            base_url=self.api_url,
            headers=_headers,
            timeout=timeout,
        )
        self._async_client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=_headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers (synchronous)
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
    # Internal helpers (asynchronous)
    # ------------------------------------------------------------------

    async def _async_raise_for_status(self, response: httpx.Response) -> None:
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise FairGuardAPIError(response.status_code, detail)

    async def _aget(self, path: str, **kwargs: Any) -> Any:
        response = await self._async_client.get(path, **kwargs)
        await self._async_raise_for_status(response)
        return response.json()

    async def _apost(self, path: str, **kwargs: Any) -> Any:
        response = await self._async_client.post(path, **kwargs)
        await self._async_raise_for_status(response)
        return response.json()

    # ------------------------------------------------------------------
    # Public API (synchronous)
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
        return _parse_audit_result(raw, project_id)

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
        audits = self._get(
            "/api/v1/audit/offline", params={"project_id": project_id}
        )
        if not audits:
            return {}
        latest = self._get(f"/api/v1/audit/offline/{audits[0]['id']}")
        return (latest.get("audit") or {}).get("metrics_json") or {}

    def get_receipt(self, receipt_id: str) -> Receipt:
        """
        Fetch a cryptographic audit receipt by ID.

        Parameters
        ----------
        receipt_id:
            The receipt identifier returned by a previous audit.

        Returns
        -------
        Receipt
            Receipt object including signature and metadata.
        """
        raw = self._get(f"/api/v1/receipts/{receipt_id}")
        return _parse_receipt(raw)

    def verify_receipt(self, receipt_id: str) -> VerificationResult:
        """
        Verify the cryptographic integrity of an audit receipt.

        Parameters
        ----------
        receipt_id:
            The receipt identifier to verify.

        Returns
        -------
        VerificationResult
            Verification result with ``valid`` boolean and details.
        """
        raw = self._post(f"/api/v1/receipts/{receipt_id}/verify")
        return VerificationResult(
            valid=raw["valid"],
            receipt_id=raw["receipt_id"],
            verified_at=raw["verified_at"],
            reason=raw.get("reason"),
        )

    def get_runtime_status(
        self,
        project_id: str,
        aggregation_key: Optional[str] = None,
    ) -> RuntimeStatus:
        """
        Get real-time monitoring status for a project.

        Parameters
        ----------
        project_id:
            Target project.
        aggregation_key:
            Optional aggregation key to scope the query.

        Returns
        -------
        RuntimeStatus
            Status payload including window-level health and metrics.
        """
        params: dict[str, str] = {"project_id": project_id}
        if aggregation_key:
            params["aggregation_key"] = aggregation_key
        raw = self._get("/api/v1/runtime/status", params=params)
        return RuntimeStatus(
            project_id=raw["project_id"],
            overall_status=raw["overall_status"],
            windows=raw.get("windows", {}),
            aggregation_key=raw.get("aggregation_key"),
        )

    def ingest_decisions(
        self,
        project_id: str,
        decisions: list[dict[str, Any]],
        model_endpoint_id: str = "sdk-client",
    ) -> dict[str, Any]:
        """
        Ingest a batch of model decisions for real-time monitoring.

        Parameters
        ----------
        project_id:
            Target project.
        decisions:
            List of decision records. Each must have ``decision_id``,
            ``sensitive_attributes``, ``outcome``, and ``timestamp``.
        model_endpoint_id:
            Identifier for the model endpoint (default: ``"sdk-client"``).

        Returns
        -------
        dict
            Ingestion confirmation.
        """
        payload = {
            "project_id": project_id,
            "model_endpoint_id": model_endpoint_id,
            "decisions": decisions,
        }
        return self._post("/api/v1/runtime/ingest", json=payload)

    # ------------------------------------------------------------------
    # Public API (asynchronous)
    # ------------------------------------------------------------------

    async def run_audit(
        self,
        project_id: str,
        data: "pd.DataFrame",
        target_col: str,
        prediction_col: str,
        sensitive_cols: list[str],
    ) -> AuditResult:
        """
        Convert a DataFrame to CSV bytes and POST as multipart to /audit/offline.

        Parameters
        ----------
        project_id:
            The FairGuard project to audit against.
        data:
            pandas DataFrame containing predictions and labels.
        target_col:
            Name of the ground-truth label column.
        prediction_col:
            Name of the model prediction column.
        sensitive_cols:
            List of sensitive attribute column names.

        Returns
        -------
        AuditResult
            Structured audit result.
        """
        csv_buffer = io.BytesIO()
        data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        files = {"file": ("data.csv", csv_buffer, "text/csv")}
        form_data = {
            "project_id": project_id,
            "target_column": target_col,
            "prediction_column": prediction_col,
            "sensitive_columns": ",".join(sensitive_cols),
        }
        response = await self._async_client.post(
            "/api/v1/audit/offline", data=form_data, files=files
        )
        await self._async_raise_for_status(response)
        raw = response.json()
        return _parse_audit_result(raw, project_id)

    async def get_runtime_status_async(
        self,
        project_id: str,
        aggregation_key: Optional[str] = None,
    ) -> RuntimeStatus:
        """Async version of :meth:`get_runtime_status`."""
        params: dict[str, str] = {"project_id": project_id}
        if aggregation_key:
            params["aggregation_key"] = aggregation_key
        raw = await self._aget("/api/v1/runtime/status", params=params)
        return RuntimeStatus(
            project_id=raw["project_id"],
            overall_status=raw["overall_status"],
            windows=raw.get("windows", {}),
            aggregation_key=raw.get("aggregation_key"),
        )

    async def ingest_decisions_async(
        self,
        project_id: str,
        decisions: list[dict[str, Any]],
        model_endpoint_id: str = "sdk-client",
    ) -> None:
        """Async version of :meth:`ingest_decisions`."""
        payload = {
            "project_id": project_id,
            "model_endpoint_id": model_endpoint_id,
            "decisions": decisions,
        }
        await self._apost("/api/v1/runtime/ingest", json=payload)

    # ------------------------------------------------------------------
    # Context manager support (sync + async)
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FairGuardClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    async def __aenter__(self) -> "FairGuardClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._async_client.aclose()


# ---------------------------------------------------------------------------
# Private parse helpers
# ---------------------------------------------------------------------------


def _parse_audit_result(raw: dict[str, Any], project_id: str) -> AuditResult:
    """Convert the AuditResultResponse dict to an :class:`AuditResult` dataclass."""
    audit = raw.get("audit") or {}
    return AuditResult(
        audit_id=str(audit.get("id", "")),
        project_id=str(audit.get("project_id", project_id)),
        verdict=str(audit.get("verdict", "unknown")),
        dataset_hash=str(audit.get("dataset_hash", "")),
        contract_evaluations=raw.get("contract_evaluations", []),
        recommendations=raw.get("recommendations", []),
        receipt_id=str(raw["receipt_id"]) if raw.get("receipt_id") else None,
    )


def _parse_receipt(raw: dict[str, Any]) -> Receipt:
    """Convert a raw receipt dict to a :class:`Receipt` dataclass."""
    return Receipt(
        id=str(raw.get("id", "")),
        audit_id=str(raw.get("audit_id", "")),
        verdict=str(raw.get("verdict", "")),
        signature=raw.get("signature"),
        public_key=raw.get("public_key"),
        created_at=str(raw.get("created_at", "")),
    )


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
) -> dict[str, Any]:
    """Module-level convenience wrapper around :meth:`FairGuardClient.get_metrics`."""
    return _get_default_client().get_metrics(project_id=project_id)


def get_receipt(receipt_id: str) -> Receipt:
    """Module-level convenience wrapper around :meth:`FairGuardClient.get_receipt`."""
    return _get_default_client().get_receipt(receipt_id=receipt_id)
