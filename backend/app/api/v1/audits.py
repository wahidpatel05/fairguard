"""API endpoints for offline fairness audits."""
from __future__ import annotations

import hashlib
import io
import logging
import traceback
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
from app.schemas.audit import (
    AuditOut,
    AuditResultResponse,
    AuditSummary,
    ContractEvaluationResult,
)
from app.services.fairness import FairnessEngine
from app.services.receipt import receipt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audits"])


# ---------------------------------------------------------------------------
# POST /audit/offline  – run an offline audit
# ---------------------------------------------------------------------------


@router.post(
    "/offline",
    response_model=AuditResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_offline_audit(
    project_id: UUID = Form(...),
    target_column: str = Form(...),
    prediction_column: str = Form(...),
    sensitive_columns: str = Form(
        ..., description="Comma-separated sensitive attribute column names"
    ),
    file: UploadFile = File(..., description="CSV file containing predictions"),
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> AuditResultResponse:
    """Upload a CSV and run a full fairness audit against the project's active contract."""

    # 1. Verify project access
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden"
        )

    # 2. Get current contract (404 if none)
    contract_result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.project_id == project_id,
            FairnessContract.is_current == True,  # noqa: E712
        )
    )
    current_contract = contract_result.scalar_one_or_none()
    if current_contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active fairness contract found for this project.",
        )

    # 3. Read file bytes, compute SHA-256 hash
    file_bytes = await file.read()
    dataset_hash = hashlib.sha256(file_bytes).hexdigest()

    # 4. Parse CSV entirely in memory
    try:
        df = pd.read_csv(io.StringIO(file_bytes.decode("utf-8")))
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not decode CSV file as UTF-8: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse CSV file: {exc}",
        ) from exc

    # 5. Split sensitive_columns string
    sensitive_cols = [c.strip() for c in sensitive_columns.split(",") if c.strip()]

    # 6. Validate columns
    required_cols = [target_column, prediction_column] + sensitive_cols
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Columns not found in CSV: {missing}",
        )

    # 7. Validate row count
    if len(df) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset must contain at least 10 rows; found {len(df)}.",
        )

    # 8–11. Fairness computation pipeline
    try:
        metrics = FairnessEngine.compute_metrics(
            df=df,
            target_col=target_column,
            prediction_col=prediction_column,
            sensitive_cols=sensitive_cols,
        )

        contract_results = FairnessEngine.evaluate_contracts(
            metrics, current_contract.contracts_json
        )

        verdict = FairnessEngine.compute_verdict(contract_results)

        failing = [r for r in contract_results if not r.get("passed", True)]
        recommendations = FairnessEngine.generate_mitigation_recommendations(failing)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error("Computation error during audit: %s", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during fairness computation.",
        ) from exc

    # 12. Persist OfflineAudit record
    audit = OfflineAudit(
        project_id=project_id,
        contract_version_id=current_contract.id,
        dataset_filename=file.filename,
        dataset_hash=dataset_hash,
        target_column=target_column,
        prediction_column=prediction_column,
        sensitive_columns=sensitive_cols,
        metrics_json={**metrics, "contract_evaluation": contract_results},
        verdict=verdict,
        triggered_by="api",
        user_id=current_user.id,
    )
    db.add(audit)
    await db.flush()
    await db.refresh(audit)

    # 13. Auto-sign and create receipt
    receipt_id: UUID | None = None
    try:
        receipt = await receipt_service.create_receipt(
            db=db,
            audit_id=audit.id,
            project_id=project_id,
            dataset_hash=dataset_hash,
            contract_version=current_contract.version,
            contracts_summary=contract_results,
            metrics_summary=metrics.get("global", {}),
            verdict=verdict,
        )
        receipt_id = receipt.id
    except Exception:
        logger.error(
            "Failed to create receipt for audit %s: %s",
            audit.id,
            traceback.format_exc(),
        )

    # 14. In-memory file buffer – never written to disk.
    del file_bytes

    # 15. Return 201
    evaluations = [ContractEvaluationResult(**r) for r in contract_results]

    return AuditResultResponse(
        audit=AuditOut.model_validate(audit),
        contract_evaluations=evaluations,
        recommendations=recommendations,
        receipt_id=receipt_id,
    )


# ---------------------------------------------------------------------------
# GET /audit/offline  – list audits for a project
# ---------------------------------------------------------------------------


@router.get("/offline", response_model=list[AuditSummary])
async def list_offline_audits(
    project_id: UUID,
    _project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> list[AuditSummary]:
    """List offline audits for a project, newest first (max 100)."""
    result = await db.execute(
        select(OfflineAudit)
        .where(OfflineAudit.project_id == project_id)
        .order_by(OfflineAudit.created_at.desc())
        .limit(100)
    )
    audits = result.scalars().all()
    return [AuditSummary.model_validate(a) for a in audits]


# ---------------------------------------------------------------------------
# GET /audit/offline/{audit_id}  – fetch a specific audit with full metrics
# ---------------------------------------------------------------------------


@router.get("/offline/{audit_id}", response_model=AuditResultResponse)
async def get_offline_audit(
    audit_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> AuditResultResponse:
    """Fetch a specific audit and re-evaluate contracts from stored metrics."""
    # Fetch audit
    audit_result = await db.execute(
        select(OfflineAudit).where(OfflineAudit.id == audit_id)
    )
    audit = audit_result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found"
        )

    # Verify project access
    proj_result = await db.execute(
        select(Project).where(Project.id == audit.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None or (
        current_user.role != "admin" and project.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden"
        )

    # Re-evaluate contracts from stored metrics and current contract
    contract_results: list[dict] = []
    failing: list[dict] = []

    if audit.metrics_json is not None:
        contract_result = await db.execute(
            select(FairnessContract).where(
                FairnessContract.project_id == audit.project_id,
                FairnessContract.is_current == True,  # noqa: E712
            )
        )
        current_contract = contract_result.scalar_one_or_none()

        if current_contract is not None:
            contract_results = FairnessEngine.evaluate_contracts(
                audit.metrics_json, current_contract.contracts_json
            )
            failing = [r for r in contract_results if not r.get("passed", True)]

    recommendations = FairnessEngine.generate_mitigation_recommendations(failing)

    # Look up associated receipt
    from app.models.receipt import FairnessReceipt  # avoid circular at module level

    receipt_row = await db.execute(
        select(FairnessReceipt).where(FairnessReceipt.audit_id == audit_id)
    )
    receipt = receipt_row.scalar_one_or_none()

    evaluations = [ContractEvaluationResult(**r) for r in contract_results]

    return AuditResultResponse(
        audit=AuditOut.model_validate(audit),
        contract_evaluations=evaluations,
        recommendations=recommendations,
        receipt_id=receipt.id if receipt else None,
    )


# ---------------------------------------------------------------------------
# Backward-compatible legacy endpoints
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/audits", response_model=list[AuditOut])
async def list_audits_legacy(
    project_id: UUID,
    _project: Project = Depends(require_project_access),
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


@router.get("/projects/{project_id}/audits/latest", response_model=AuditOut)
async def get_latest_audit_legacy(
    project_id: UUID,
    _project: Project = Depends(require_project_access),
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


@router.get("/{audit_id}", response_model=AuditOut)
async def get_audit_legacy(
    audit_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> AuditOut:
    """Retrieve a specific offline audit by ID (legacy path)."""
    result = await db.execute(
        select(OfflineAudit).where(OfflineAudit.id == audit_id)
    )
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found"
        )

    proj_result = await db.execute(
        select(Project).where(Project.id == audit.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None or (
        current_user.role != "admin" and project.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden"
        )

    return AuditOut.model_validate(audit)
