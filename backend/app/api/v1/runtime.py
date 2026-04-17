"""API endpoints for runtime monitoring, firewall proxy, and snapshot management."""
from __future__ import annotations

import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_project_access
from app.core.security import get_current_user_either
from app.models.runtime import RuntimeDecision, RuntimeSnapshot
from app.models.user import User
from app.schemas.runtime import (
    IngestDecisionsRequest,
    RuntimeStatusResponse,
    RuntimeWindowStatus,
    SnapshotOut,
)
from app.services.runtime import get_current_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime", tags=["runtime"])


# ---------------------------------------------------------------------------
# POST /runtime/ingest
# ---------------------------------------------------------------------------


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_decisions(
    body: IngestDecisionsRequest,
    current_user: User = Depends(get_current_user_either),
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk-ingest model decisions and trigger async snapshot recomputation."""

    rows = [
        {
            "project_id": body.project_id,
            "model_endpoint_id": body.model_endpoint_id,
            "aggregation_key": body.aggregation_key,
            "decision_id": d.decision_id,
            "sensitive_attributes": d.sensitive_attributes,
            "outcome": d.outcome,
            "ground_truth": d.ground_truth,
            "timestamp": d.timestamp,
        }
        for d in body.decisions
    ]

    await db.execute(insert(RuntimeDecision), rows)
    await db.commit()

    from app.tasks.runtime_tasks import recompute_snapshots_task

    recompute_snapshots_task.delay(str(body.project_id), body.aggregation_key)

    return {
        "accepted": len(body.decisions),
        "message": "Decisions ingested, snapshots updating",
    }


# ---------------------------------------------------------------------------
# GET /runtime/status
# ---------------------------------------------------------------------------


@router.get("/status", response_model=RuntimeStatusResponse)
async def get_runtime_status(
    project_id: UUID = Query(...),
    aggregation_key: str | None = Query(None),
    current_user: User = Depends(get_current_user_either),
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> RuntimeStatusResponse:
    """Return the current fairness status for all 4 time windows."""
    status_data = await get_current_status(db, project_id, aggregation_key)

    windows = {
        wt: RuntimeWindowStatus(
            metrics=wdata.get("metrics", {}),
            status=wdata.get("status", "insufficient_data"),
            evaluated_at=wdata.get("evaluated_at"),
            count=wdata.get("count", 0),
        )
        for wt, wdata in status_data["windows"].items()
    }

    return RuntimeStatusResponse(
        project_id=status_data["project_id"],
        aggregation_key=status_data["aggregation_key"],
        windows=windows,
        overall_status=status_data["overall_status"],
    )


# ---------------------------------------------------------------------------
# POST /runtime/proxy/{project_id}
# ---------------------------------------------------------------------------


@router.post("/proxy/{project_id}")
async def proxy_request(
    project_id: UUID,
    request: Request,
    x_downstream_url: str | None = Header(None, alias="X-Downstream-URL"),
    x_outcome_path: str | None = Header(None, alias="X-Outcome-Path"),
    x_fail_mode: str | None = Header(None, alias="X-Fail-Mode"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Fairness-aware reverse proxy.

    Checks runtime fairness status before forwarding to the downstream URL.
    In 'closed' fail-mode, blocks requests when status is critical.
    """
    if x_downstream_url is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "missing_header", "detail": "X-Downstream-URL header is required"},
        )

    # Validate scheme to prevent SSRF against internal services via non-HTTP protocols.
    # Only http and https are permitted; this endpoint is intended to proxy external
    # model endpoints authenticated by the API key on the caller side.
    from urllib.parse import urlparse

    parsed_url = urlparse(x_downstream_url)
    if parsed_url.scheme not in ("http", "https"):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_downstream_url",
                "detail": "X-Downstream-URL must use http or https scheme",
            },
        )

    fail_mode = (x_fail_mode or "open").lower()

    # Check current fairness status
    try:
        current_status_data = await get_current_status(db, project_id, None)
        overall_status = current_status_data.get("overall_status", "no_data")
    except Exception:
        logger.exception("Failed to get runtime status for project %s", project_id)
        overall_status = "no_data"

    # Block in closed fail-mode when critical
    if overall_status == "critical" and fail_mode == "closed":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "fairness_block",
                "status": "critical",
                "message": "Request blocked by FairGuard runtime firewall",
            },
        )

    # Read raw request body
    body_bytes = await request.body()

    # Forward headers (strip FairGuard-specific ones)
    _strip_headers = {
        "x-downstream-url",
        "x-outcome-path",
        "x-fail-mode",
        "host",
        "content-length",
    }
    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _strip_headers
    }

    # Forward request to downstream
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            downstream_response = await client.request(
                method=request.method,
                url=x_downstream_url,
                content=body_bytes,
                headers=forward_headers,
            )
    except httpx.TimeoutException:
        if fail_mode == "closed":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"error": "upstream_timeout"},
            )
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"error": "upstream_timeout", "fail_mode": "open"},
        )

    # Extract outcome from response using X-Outcome-Path
    outcome_str: str
    try:
        if x_outcome_path:
            response_json = downstream_response.json()
            parts = x_outcome_path.split(".")
            value = response_json
            for part in parts:
                value = value[part]
            outcome_str = str(value)
        else:
            outcome_str = str(downstream_response.status_code)
    except Exception:
        outcome_str = str(downstream_response.status_code)

    # Fire-and-forget: ingest decision and trigger snapshot recomputation
    try:
        from datetime import datetime, timezone

        decision_row = {
            "project_id": project_id,
            "model_endpoint_id": "proxy",
            "aggregation_key": None,
            "decision_id": str(id(downstream_response)),
            "sensitive_attributes": {},
            "outcome": outcome_str,
            "ground_truth": None,
            "timestamp": datetime.now(timezone.utc),
        }
        await db.execute(insert(RuntimeDecision), [decision_row])
        await db.commit()

        from app.tasks.runtime_tasks import recompute_snapshots_task

        recompute_snapshots_task.delay(str(project_id), None)
    except Exception:
        logger.exception(
            "Failed to ingest proxy decision for project %s", project_id
        )

    # Return downstream response verbatim
    return Response(
        content=downstream_response.content,
        status_code=downstream_response.status_code,
        headers=dict(downstream_response.headers),
        media_type=downstream_response.headers.get("content-type"),
    )


# ---------------------------------------------------------------------------
# GET /runtime/snapshots
# ---------------------------------------------------------------------------


@router.get("/snapshots", response_model=list[SnapshotOut])
async def list_snapshots(
    project_id: UUID = Query(...),
    aggregation_key: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user_either),
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> list[SnapshotOut]:
    """List runtime snapshots for a project, newest first."""
    stmt = (
        select(RuntimeSnapshot)
        .where(
            RuntimeSnapshot.project_id == project_id,
            RuntimeSnapshot.aggregation_key == aggregation_key,
        )
        .order_by(RuntimeSnapshot.evaluated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    return [SnapshotOut.model_validate(s) for s in snapshots]
