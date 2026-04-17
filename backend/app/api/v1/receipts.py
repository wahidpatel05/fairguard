"""API endpoints for fairness audit receipts."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_project_access
from app.core.security import get_current_user_either
from app.models.project import Project
from app.models.receipt import FairnessReceipt
from app.models.user import User
from app.schemas.receipt import ReceiptOut, VerifyReceiptResponse
from app.services.receipt import receipt_service

router = APIRouter(prefix="/receipts", tags=["receipts"])


# ---------------------------------------------------------------------------
# GET /receipts/  – list receipts for a project
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[ReceiptOut])
async def list_receipts(
    project_id: UUID,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    _project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> list[ReceiptOut]:
    """List receipts for a project with optional date range filter."""
    query = (
        select(FairnessReceipt)
        .where(FairnessReceipt.project_id == project_id)
        .order_by(FairnessReceipt.created_at.desc())
    )
    if from_date is not None:
        query = query.where(FairnessReceipt.created_at >= from_date)
    if to_date is not None:
        query = query.where(FairnessReceipt.created_at <= to_date)

    result = await db.execute(query)
    receipts = result.scalars().all()
    return [ReceiptOut.model_validate(r) for r in receipts]


# ---------------------------------------------------------------------------
# GET /receipts/{receipt_id}  – get a specific receipt
# ---------------------------------------------------------------------------


@router.get("/{receipt_id}", response_model=ReceiptOut)
async def get_receipt(
    receipt_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> ReceiptOut:
    """Fetch a specific receipt and verify project access."""
    result = await db.execute(
        select(FairnessReceipt).where(FairnessReceipt.id == receipt_id)
    )
    receipt = result.scalar_one_or_none()
    if receipt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    # Verify project access
    proj_result = await db.execute(
        select(Project).where(Project.id == receipt.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None or (
        current_user.role != "admin" and project.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden"
        )

    return ReceiptOut.model_validate(receipt)


# ---------------------------------------------------------------------------
# POST /receipts/{receipt_id}/verify  – verify receipt signature
# ---------------------------------------------------------------------------


@router.post("/{receipt_id}/verify", response_model=VerifyReceiptResponse)
async def verify_receipt(
    receipt_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> VerifyReceiptResponse:
    """Verify the Ed25519 signature on a fairness receipt."""
    # Access-check: ensure the receipt exists and user has access to its project
    result = await db.execute(
        select(FairnessReceipt).where(FairnessReceipt.id == receipt_id)
    )
    receipt = result.scalar_one_or_none()
    if receipt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    proj_result = await db.execute(
        select(Project).where(Project.id == receipt.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if project is None or (
        current_user.role != "admin" and project.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden"
        )

    verification = await receipt_service.verify_receipt_by_id(db, receipt_id)
    return VerifyReceiptResponse(**verification)
