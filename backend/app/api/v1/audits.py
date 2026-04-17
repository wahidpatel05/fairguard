"""API endpoints for offline fairness audits."""
from __future__ import annotations

import io
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_project_access
from app.core.security import get_current_user_either
from app.models.audit import OfflineAudit
from app.models.contract import FairnessContract
from app.models.project import Project
from app.models.user import User
from app.schemas.audit import AuditOut
from app.services.fairness import FairnessEngine
from services.fairness import (
    compute_dataset_hash,
    evaluate_contracts,
    determine_overall_verdict,
)

router = APIRouter(tags=["audits"])


# ---------------------------------------------------------------------------
# POST /audit/offline  – run an offline audit
# ---------------------------------------------------------------------------

@router.post("/audit/offline", response_model=AuditOut, status_code=status.HTTP_201_CREATED)
async def run_offline_audit(
    project_id: UUID = Form(...),
    target_column: str = Form(...),
    prediction_column: str = Form(...),
    sensitive_columns: str = Form(..., description="Comma-separated column names"),
    file: UploadFile = File(..., description="CSV file containing predictions"),
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> AuditOut:
    """Upload a CSV and run a full fairness audit against the project's active contract."""
    # Verify project access
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    # Parse uploaded CSV
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse CSV: {exc}",
        ) from exc

    sensitive_cols = [c.strip() for c in sensitive_columns.split(",") if c.strip()]

    # Compute fairness metrics via FairnessEngine
    try:
        metrics = FairnessEngine.compute_metrics(
            df=df,
            target_col=target_column,
            prediction_col=prediction_column,
            sensitive_cols=sensitive_cols,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Compute dataset hash (on the raw bytes)
    dataset_hash = compute_dataset_hash(df)

    # Evaluate against active contract (if any)
    contract_version_id: UUID | None = None
    verdict = "pass"

    active_result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.project_id == project_id,
            FairnessContract.is_current == True,  # noqa: E712
        )
    )
    active_contract = active_result.scalar_one_or_none()

    if active_contract is not None:
        contract_version_id = active_contract.id
        rules = active_contract.contracts_json.get("rules", [])
        # Build flat metrics dict for evaluate_contracts (by_attribute format)
        flat_metrics: dict = {}
        for attr, attr_data in metrics["by_attribute"].items():
            flat_metrics[attr] = {
                "disparate_impact": attr_data["disparate_impact"],
                "tpr_gap": attr_data["tpr_difference"],
                "tpr_difference": attr_data["tpr_difference"],
                "fpr_gap": attr_data["fpr_difference"],
                "accuracy_gap": attr_data["accuracy_difference"],
            }
        contract_results = evaluate_contracts(flat_metrics, rules)
        verdict = determine_overall_verdict(contract_results)
        # Embed contract evaluation into metrics
        metrics["contract_evaluation"] = contract_results

    # Persist the audit record
    audit = OfflineAudit(
        project_id=project_id,
        contract_version_id=contract_version_id,
        dataset_filename=file.filename,
        dataset_hash=dataset_hash,
        target_column=target_column,
        prediction_column=prediction_column,
        sensitive_columns=sensitive_cols,
        metrics_json=metrics,
        verdict=verdict,
        triggered_by="api",
        user_id=current_user.id,
    )
    db.add(audit)
    await db.flush()
    await db.refresh(audit)
    return AuditOut.model_validate(audit)


# ---------------------------------------------------------------------------
# GET /audit/{audit_id}  – retrieve a specific audit
# ---------------------------------------------------------------------------

@router.get("/audit/{audit_id}", response_model=AuditOut)
async def get_audit(
    audit_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> AuditOut:
    """Retrieve a specific offline audit by ID."""
    result = await db.execute(
        select(OfflineAudit).where(OfflineAudit.id == audit_id)
    )
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")

    # Check project access
    proj_result = await db.execute(
        select(Project).where(Project.id == audit.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None or (
        current_user.role != "admin" and project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    return AuditOut.model_validate(audit)


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/audits  – list audits for a project
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/audits", response_model=list[AuditOut])
async def list_audits(
    project_id: UUID,
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> list[AuditOut]:
    """List all offline audits for a project, newest first."""
    result = await db.execute(
        select(OfflineAudit)
        .where(OfflineAudit.project_id == project_id)
        .order_by(OfflineAudit.created_at.desc())
    )
    audits = result.scalars().all()
    return [AuditOut.model_validate(a) for a in audits]


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/audits/latest  – latest audit for a project
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/audits/latest", response_model=AuditOut)
async def get_latest_audit(
    project_id: UUID,
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> AuditOut:
    """Return the most recent offline audit for a project."""
    result = await db.execute(
        select(OfflineAudit)
        .where(OfflineAudit.project_id == project_id)
        .order_by(OfflineAudit.created_at.desc())
        .limit(1)
    )
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audits found for this project.",
        )
    return AuditOut.model_validate(audit)
