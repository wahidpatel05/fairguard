"""Offline audit endpoints."""
import base64
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.config import settings
from core.database import get_db
from core.schemas import AuditResponse, AuditLogResponse, ContractStatus
from models.db import AuditLog, FairnessContract, FairnessReceipt, Project, User
from services.fairness import (
    compute_dataset_hash,
    compute_fairness_metrics,
    determine_overall_verdict,
    evaluate_contracts,
)
from services.signing import sign_receipt

router = APIRouter(prefix="/audit", tags=["audits"])


@router.post("/offline", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
async def run_offline_audit(
    csv_file: UploadFile = File(...),
    project_id: uuid.UUID = Form(...),
    target_column: str = Form(...),
    prediction_column: str = Form(...),
    sensitive_columns: str = Form(...),
    endpoint_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run an offline fairness audit on an uploaded CSV file.

    Computes fairness metrics, evaluates active contracts, generates a signed receipt.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    content = await csv_file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    sensitive_cols = [c.strip() for c in sensitive_columns.split(",") if c.strip()]
    for col in [target_column, prediction_column] + sensitive_cols:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{col}' not found in CSV")

    dataset_hash = compute_dataset_hash(df)
    metrics = compute_fairness_metrics(df, target_column, prediction_column, sensitive_cols)

    # Load active contracts
    result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.project_id == project_id,
            FairnessContract.is_active == True,
        )
    )
    active_contracts = result.scalars().all()

    contract_rules = []
    contract_version = None
    contract_id_used = None
    for c in active_contracts:
        rules = c.contract_json.get("rules", [])
        for rule in rules:
            rule["id"] = str(c.id)
        contract_rules.extend(rules)
        contract_version = c.version
        contract_id_used = c.id

    contract_statuses_raw = evaluate_contracts(metrics, contract_rules)
    verdict = determine_overall_verdict(contract_statuses_raw)

    audit_log = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        contract_id=contract_id_used,
        contract_version=contract_version,
        dataset_hash=dataset_hash,
        metrics_json=metrics,
        verdict=verdict,
        endpoint_id=endpoint_id,
    )
    db.add(audit_log)
    await db.flush()

    # Build and sign receipt
    receipt_payload = {
        "audit_log_id": str(audit_log.id),
        "project_id": str(project_id),
        "dataset_hash": dataset_hash,
        "contract_version": contract_version,
        "verdict": verdict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    private_key_bytes = base64.b64decode(settings.SIGNING_PRIVATE_KEY)
    public_key_bytes = base64.b64decode(settings.SIGNING_PUBLIC_KEY)
    signature = sign_receipt(receipt_payload, private_key_bytes)

    receipt = FairnessReceipt(
        audit_log_id=audit_log.id,
        project_id=project_id,
        endpoint_id=endpoint_id,
        dataset_hash=dataset_hash,
        contract_version=contract_version,
        contracts_list={"rules": contract_rules, "statuses": contract_statuses_raw},
        metrics_summary=metrics,
        verdict=verdict,
        signature=signature,
        public_key=public_key_bytes,
    )
    db.add(receipt)
    await db.flush()
    await db.refresh(receipt)

    contract_statuses = [ContractStatus(**s) for s in contract_statuses_raw]

    return AuditResponse(
        audit_log_id=audit_log.id,
        receipt_id=receipt.id,
        project_id=project_id,
        dataset_hash=dataset_hash,
        metrics=metrics,
        contract_statuses=contract_statuses,
        verdict=verdict,
        timestamp=audit_log.timestamp,
    )


@router.get("/logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    project_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs, optionally filtered by project."""
    query = select(AuditLog)
    if project_id:
        query = query.where(AuditLog.project_id == project_id)
    elif current_user.role != "admin":
        query = query.where(AuditLog.user_id == current_user.id)
    result = await db.execute(query.order_by(AuditLog.timestamp.desc()))
    return result.scalars().all()


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific audit log entry."""
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    if current_user.role != "admin" and log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return log
