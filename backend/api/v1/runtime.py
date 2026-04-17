"""Runtime firewall endpoints for live decision ingestion and monitoring."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from core.schemas import (
    RuntimeIngestRequest,
    RuntimeIngestResponse,
    RuntimeStatusResponse,
    RuntimeMetricsHistory,
)
from models.db import FairnessContract, Project, RuntimeMetrics, User
from services.runtime_monitor import runtime_monitor

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.post("/ingest", response_model=RuntimeIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_decisions(
    ingest: RuntimeIngestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest one or more runtime decisions for fairness monitoring."""
    result = await db.execute(select(Project).where(Project.id == ingest.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    for decision in ingest.decisions:
        await runtime_monitor.ingest_decision(
            project_id=ingest.project_id,
            endpoint_id=decision.endpoint_id,
            decision_data=decision.model_dump(),
            db=db,
        )

    return RuntimeIngestResponse(ingested=len(ingest.decisions), project_id=ingest.project_id)


@router.get("/status", response_model=RuntimeStatusResponse)
async def get_runtime_status(
    project_id: uuid.UUID,
    endpoint_id: str,
    window: str = "1hr",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current fairness metrics and contract status for an endpoint."""
    if window not in {"1hr", "24hr", "rolling_n"}:
        raise HTTPException(status_code=400, detail="window must be one of: 1hr, 24hr, rolling_n")

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    metrics = await runtime_monitor.get_rolling_metrics(project_id, endpoint_id, window, db)

    result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.project_id == project_id,
            FairnessContract.is_active.is_(True),
        )
    )
    contracts = result.scalars().all()
    contract_rules = []
    for c in contracts:
        contract_rules.extend(c.contract_json.get("rules", []))

    runtime_status = runtime_monitor.evaluate_status(metrics, contract_rules or None)
    await runtime_monitor.save_metrics_snapshot(project_id, endpoint_id, window, metrics, runtime_status, db)

    return RuntimeStatusResponse(
        project_id=project_id,
        endpoint_id=endpoint_id,
        window=window,
        metrics=metrics,
        status=runtime_status,
        computed_at=datetime.now(timezone.utc),
    )


@router.get("/metrics/history", response_model=RuntimeMetricsHistory)
async def get_metrics_history(
    project_id: uuid.UUID,
    endpoint_id: str,
    window: str = "1hr",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve historical metrics snapshots for charts."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(RuntimeMetrics).where(
            RuntimeMetrics.project_id == project_id,
            RuntimeMetrics.endpoint_id == endpoint_id,
            RuntimeMetrics.window_type == window,
        ).order_by(RuntimeMetrics.computed_at.desc()).limit(100)
    )
    snapshots = result.scalars().all()
    history = [
        {
            "computed_at": s.computed_at.isoformat(),
            "status": s.status,
            **s.metrics_json,
        }
        for s in snapshots
    ]
    return RuntimeMetricsHistory(
        project_id=project_id,
        endpoint_id=endpoint_id,
        window=window,
        history=history,
    )
