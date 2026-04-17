"""Fairness receipt endpoints."""
import base64
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from core.schemas import ReceiptResponse, ReceiptVerifyResponse
from models.db import FairnessReceipt, Project, User
from services.signing import verify_receipt

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("", response_model=list[ReceiptResponse])
async def list_receipts(
    project_id: Optional[uuid.UUID] = None,
    endpoint_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List fairness receipts with optional filters."""
    query = select(FairnessReceipt)
    if project_id:
        query = query.where(FairnessReceipt.project_id == project_id)
    if endpoint_id:
        query = query.where(FairnessReceipt.endpoint_id == endpoint_id)
    if from_date:
        query = query.where(FairnessReceipt.timestamp >= from_date)
    if to_date:
        query = query.where(FairnessReceipt.timestamp <= to_date)
    if current_user.role != "admin":
        query = query.join(Project, FairnessReceipt.project_id == Project.id).where(
            Project.owner_id == current_user.id
        )
    result = await db.execute(query.order_by(FairnessReceipt.timestamp.desc()))
    receipts = result.scalars().all()
    return [_receipt_to_response(r) for r in receipts]


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific fairness receipt by ID."""
    result = await db.execute(select(FairnessReceipt).where(FairnessReceipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if current_user.role != "admin":
        proj_result = await db.execute(select(Project).where(Project.id == receipt.project_id))
        project = proj_result.scalar_one_or_none()
        if not project or project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return _receipt_to_response(receipt)


@router.post("/{receipt_id}/verify", response_model=ReceiptVerifyResponse)
async def verify_receipt_endpoint(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify the Ed25519 signature on a fairness receipt."""
    result = await db.execute(select(FairnessReceipt).where(FairnessReceipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    receipt_data = {
        "audit_log_id": str(receipt.audit_log_id),
        "project_id": str(receipt.project_id),
        "dataset_hash": receipt.dataset_hash,
        "contract_version": receipt.contract_version,
        "verdict": receipt.verdict,
        "timestamp": receipt.timestamp.isoformat(),
    }
    valid = verify_receipt(receipt_data, receipt.signature, receipt.public_key)
    details = "Signature is valid and receipt is authentic." if valid else "Signature verification failed; receipt may have been tampered with."
    return ReceiptVerifyResponse(valid=valid, receipt_id=receipt_id, details=details)


def _receipt_to_response(receipt: FairnessReceipt) -> ReceiptResponse:
    """Convert a FairnessReceipt ORM object to ReceiptResponse with base64-encoded bytes."""
    return ReceiptResponse(
        id=receipt.id,
        audit_log_id=receipt.audit_log_id,
        project_id=receipt.project_id,
        endpoint_id=receipt.endpoint_id,
        dataset_hash=receipt.dataset_hash,
        contract_version=receipt.contract_version,
        contracts_list=receipt.contracts_list,
        metrics_summary=receipt.metrics_summary,
        verdict=receipt.verdict,
        signature=base64.b64encode(receipt.signature).decode(),
        public_key=base64.b64encode(receipt.public_key).decode(),
        timestamp=receipt.timestamp,
    )
