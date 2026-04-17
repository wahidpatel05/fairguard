"""Runtime monitoring service: window queries, snapshot computation, and status."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pandas as pd
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import FairnessContract
from app.models.runtime import RuntimeDecision, RuntimeSnapshot
from app.services.fairness import FairnessEngine

logger = logging.getLogger(__name__)

_WINDOW_TYPES = ["last_100", "last_1000", "last_1hr", "last_24hr"]


async def get_decisions_for_window(
    db: AsyncSession,
    project_id: UUID,
    aggregation_key: str | None,
    window_type: str,
) -> pd.DataFrame:
    """Query runtime_decisions for a given project/key and apply window filter.

    Returns a DataFrame with columns matching the runtime_decisions schema.
    Returns an empty DataFrame if no rows match.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        select(RuntimeDecision)
        .where(RuntimeDecision.project_id == project_id)
        .order_by(RuntimeDecision.timestamp.desc())
    )

    if aggregation_key is not None:
        stmt = stmt.where(RuntimeDecision.aggregation_key == aggregation_key)

    # Time-based windows: add WHERE before executing
    if window_type == "last_1hr":
        cutoff = now - timedelta(hours=1)
        stmt = stmt.where(RuntimeDecision.timestamp >= cutoff)
    elif window_type == "last_24hr":
        cutoff = now - timedelta(hours=24)
        stmt = stmt.where(RuntimeDecision.timestamp >= cutoff)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return pd.DataFrame()

    # Apply row-count limits after fetching
    if window_type == "last_100":
        rows = rows[:100]
    elif window_type == "last_1000":
        rows = rows[:1000]

    records = [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "model_endpoint_id": r.model_endpoint_id,
            "aggregation_key": r.aggregation_key,
            "decision_id": r.decision_id,
            "sensitive_attributes": r.sensitive_attributes or {},
            "outcome": r.outcome,
            "ground_truth": r.ground_truth,
            "timestamp": r.timestamp,
            "ingested_at": r.ingested_at,
        }
        for r in rows
    ]

    return pd.DataFrame(records)


async def compute_snapshot(
    db: AsyncSession,
    project_id: UUID,
    aggregation_key: str | None,
    window_type: str,
    contracts: list[dict],
) -> dict:
    """Compute fairness metrics snapshot for a given window.

    Returns a dict with keys: status, metrics, contract_evaluations, count.
    """
    df = await get_decisions_for_window(db, project_id, aggregation_key, window_type)

    if len(df) < 10:
        return {"status": "insufficient_data", "metrics": {}, "count": len(df)}

    # Expand sensitive_attributes JSONB column into individual columns
    first_non_null = next(
        (row for row in df["sensitive_attributes"] if row and isinstance(row, dict)),
        None,
    )
    sensitive_cols: list[str] = list(first_non_null.keys()) if first_non_null else []

    for col in sensitive_cols:
        df[col] = df["sensitive_attributes"].apply(
            lambda x, c=col: x.get(c) if isinstance(x, dict) else None
        )

    # Convert outcome to int (handles '1'/'0', True/False, 1/0)
    def _to_int(val: object) -> int | None:
        if val is None:
            return None
        if isinstance(val, bool):
            return int(val)
        try:
            return int(str(val))
        except (ValueError, TypeError):
            return None

    df["outcome_int"] = df["outcome"].apply(_to_int)

    # ground_truth column: use if present and not null
    has_ground_truth = (
        "ground_truth" in df.columns
        and df["ground_truth"].notna().any()
    )
    if has_ground_truth:
        df["ground_truth_int"] = df["ground_truth"].apply(_to_int)
        target_col = "ground_truth_int"
    else:
        target_col = "outcome_int"

    prediction_col = "outcome_int"

    # Drop rows with null outcome
    df = df.dropna(subset=[prediction_col])
    if has_ground_truth:
        df = df.dropna(subset=[target_col])

    if len(df) < 10:
        return {"status": "insufficient_data", "metrics": {}, "count": len(df)}

    # If no sensitive columns, return a basic snapshot without per-attribute metrics
    if not sensitive_cols:
        metrics: dict = {
            "global": {
                "total_rows": len(df),
                "positive_outcome_rate": float((df[prediction_col] == 1).mean()),
                "overall_accuracy": 1.0,
            },
            "by_attribute": {},
        }
        contract_evaluations: list[dict] = []
    else:
        # Drop rows missing any sensitive column value
        df = df.dropna(subset=sensitive_cols)
        if len(df) < 10:
            return {"status": "insufficient_data", "metrics": {}, "count": len(df)}

        try:
            metrics = FairnessEngine.compute_metrics(
                df,
                target_col=target_col,
                prediction_col=prediction_col,
                sensitive_cols=sensitive_cols,
            )
        except Exception:
            logger.exception(
                "FairnessEngine.compute_metrics failed for project %s window %s",
                project_id,
                window_type,
            )
            return {"status": "insufficient_data", "metrics": {}, "count": len(df)}

        contracts_json = {"rules": contracts} if contracts else {}
        try:
            contract_evaluations = FairnessEngine.evaluate_contracts(
                metrics, contracts_json
            )
        except Exception:
            logger.exception(
                "FairnessEngine.evaluate_contracts failed for project %s window %s",
                project_id,
                window_type,
            )
            contract_evaluations = []

    # Determine overall status from contract evaluations
    status_value = "healthy"
    for ev in contract_evaluations:
        if not ev.get("passed", True):
            severity = ev.get("severity", "warn")
            if severity == "block":
                status_value = "critical"
                break
            elif severity == "warn" and status_value != "critical":
                status_value = "warning"

    return {
        "status": status_value,
        "metrics": metrics,
        "contract_evaluations": contract_evaluations,
        "count": len(df),
    }


async def recompute_all_snapshots(
    db: AsyncSession,
    project_id: UUID,
    aggregation_key: str | None,
) -> dict[str, dict]:
    """Recompute snapshots for all 4 windows and upsert into runtime_snapshots.

    Returns a dict of {window_type: snapshot_result}.
    """
    # Fetch current contract
    contract_result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.project_id == project_id,
            FairnessContract.is_current.is_(True),
        )
    )
    current_contract = contract_result.scalar_one_or_none()
    contracts: list[dict] = []
    if current_contract is not None:
        contracts_json = current_contract.contracts_json or {}
        contracts = contracts_json.get("rules", [])

    results: dict[str, dict] = {}
    now = datetime.now(timezone.utc)

    for window_type in _WINDOW_TYPES:
        snapshot_data = await compute_snapshot(
            db, project_id, aggregation_key, window_type, contracts
        )

        # Determine DB status (only valid enum values)
        db_status = snapshot_data.get("status", "healthy")
        if db_status not in ("healthy", "warning", "critical"):
            db_status = "healthy"

        metrics_to_store = snapshot_data.get("metrics", {})

        # Upsert into runtime_snapshots
        existing_result = await db.execute(
            select(RuntimeSnapshot).where(
                RuntimeSnapshot.project_id == project_id,
                RuntimeSnapshot.aggregation_key == aggregation_key,
                RuntimeSnapshot.window_type == window_type,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            await db.execute(
                update(RuntimeSnapshot)
                .where(RuntimeSnapshot.id == existing.id)
                .values(
                    metrics_json=metrics_to_store,
                    status=db_status,
                    evaluated_at=now,
                )
            )
        else:
            await db.execute(
                insert(RuntimeSnapshot).values(
                    project_id=project_id,
                    aggregation_key=aggregation_key,
                    window_type=window_type,
                    metrics_json=metrics_to_store,
                    status=db_status,
                    evaluated_at=now,
                )
            )

        snapshot_data["evaluated_at"] = now.isoformat()
        results[window_type] = snapshot_data

    await db.commit()
    return results


async def get_current_status(
    db: AsyncSession,
    project_id: UUID,
    aggregation_key: str | None,
) -> dict:
    """Return a summary of all 4 window snapshots for a project/aggregation_key.

    Refreshes stale snapshots (older than 5 minutes) before returning.
    """
    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(minutes=5)

    # Fetch all snapshots for this project / aggregation_key
    snap_result = await db.execute(
        select(RuntimeSnapshot).where(
            RuntimeSnapshot.project_id == project_id,
            RuntimeSnapshot.aggregation_key == aggregation_key,
        )
    )
    snapshots = {s.window_type: s for s in snap_result.scalars().all()}

    # Check staleness – if any are stale or missing, recompute
    needs_refresh = any(
        window_type not in snapshots
        or (
            snapshots[window_type].evaluated_at is not None
            and snapshots[window_type].evaluated_at.replace(tzinfo=timezone.utc)
            < stale_threshold
        )
        for window_type in _WINDOW_TYPES
    )

    if needs_refresh:
        await recompute_all_snapshots(db, project_id, aggregation_key)
        # Re-fetch updated snapshots
        snap_result2 = await db.execute(
            select(RuntimeSnapshot).where(
                RuntimeSnapshot.project_id == project_id,
                RuntimeSnapshot.aggregation_key == aggregation_key,
            )
        )
        snapshots = {s.window_type: s for s in snap_result2.scalars().all()}

    windows: dict[str, dict] = {}
    status_priority = {"critical": 2, "warning": 1, "healthy": 0, "insufficient_data": -1}
    overall_priority = -1

    for window_type in _WINDOW_TYPES:
        snap = snapshots.get(window_type)
        if snap is None:
            windows[window_type] = {
                "metrics": {},
                "status": "insufficient_data",
                "evaluated_at": None,
                "count": 0,
            }
        else:
            win_status = snap.status if snap.status else "insufficient_data"
            windows[window_type] = {
                "metrics": snap.metrics_json or {},
                "status": win_status,
                "evaluated_at": snap.evaluated_at.isoformat() if snap.evaluated_at else None,
                "count": (snap.metrics_json or {}).get("global", {}).get("total_rows", 0),
            }
            priority = status_priority.get(win_status, -1)
            if priority > overall_priority:
                overall_priority = priority

    if overall_priority == -1:
        overall_status = "no_data"
    elif overall_priority == 0:
        overall_status = "healthy"
    elif overall_priority == 1:
        overall_status = "warning"
    else:
        overall_status = "critical"

    return {
        "project_id": str(project_id),
        "aggregation_key": aggregation_key,
        "windows": windows,
        "overall_status": overall_status,
    }
