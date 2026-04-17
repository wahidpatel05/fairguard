"""API endpoints for managing Fairness Contracts (versioned rule sets)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_project_access, require_project_owner_or_admin
from app.core.security import get_current_user_either
from app.models.contract import FairnessContract
from app.models.user import User
from app.schemas.contract import ContractCreate, ContractOut

router = APIRouter(prefix="/projects/{project_id}/contracts", tags=["contracts"])


@router.get("/", response_model=list[ContractOut])
async def list_contracts(
    project_id: UUID,
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> list[ContractOut]:
    """List all contract versions for a project, newest first."""
    result = await db.execute(
        select(FairnessContract)
        .where(FairnessContract.project_id == project_id)
        .order_by(FairnessContract.version.desc())
    )
    contracts = result.scalars().all()
    return [ContractOut.model_validate(c) for c in contracts]


@router.post("/", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def create_contract(
    project_id: UUID,
    payload: ContractCreate,
    current_user: User = Depends(require_project_owner_or_admin),
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> ContractOut:
    """Create a new contract version for a project.

    The new version number is automatically set to max(existing) + 1.
    The contract is *not* automatically made current; call the activate
    endpoint to promote it.
    """
    result = await db.execute(
        select(FairnessContract.version)
        .where(FairnessContract.project_id == project_id)
        .order_by(FairnessContract.version.desc())
        .limit(1)
    )
    latest_version = result.scalar_one_or_none()
    next_version = (latest_version or 0) + 1

    contract = FairnessContract(
        project_id=project_id,
        version=next_version,
        is_current=False,
        contracts_json={"rules": [r.model_dump() for r in payload.contracts]},
        created_by=current_user.id,
        notes=payload.notes,
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return ContractOut.model_validate(contract)


@router.get("/current", response_model=ContractOut)
async def get_current_contract(
    project_id: UUID,
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> ContractOut:
    """Return the currently active contract for a project."""
    result = await db.execute(
        select(FairnessContract)
        .where(
            FairnessContract.project_id == project_id,
            FairnessContract.is_current == True,  # noqa: E712
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active contract found for this project.",
        )
    return ContractOut.model_validate(contract)


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(
    project_id: UUID,
    contract_id: UUID,
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> ContractOut:
    """Return a specific contract version by its ID."""
    result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.id == contract_id,
            FairnessContract.project_id == project_id,
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )
    return ContractOut.model_validate(contract)


@router.post("/{contract_id}/activate", response_model=ContractOut)
async def activate_contract(
    project_id: UUID,
    contract_id: UUID,
    current_user: User = Depends(require_project_owner_or_admin),
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> ContractOut:
    """Promote a contract version to be the current active contract.

    Deactivates any previously active contract for the same project.
    """
    # Deactivate all existing current contracts for this project
    result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.project_id == project_id,
            FairnessContract.is_current == True,  # noqa: E712
        )
    )
    for old in result.scalars().all():
        old.is_current = False

    # Activate the target contract
    result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.id == contract_id,
            FairnessContract.project_id == project_id,
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )

    contract.is_current = True
    await db.flush()
    await db.refresh(contract)
    return ContractOut.model_validate(contract)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    project_id: UUID,
    contract_id: UUID,
    current_user: User = Depends(require_project_owner_or_admin),
    _project=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a contract version.

    A currently active (``is_current=True``) contract cannot be deleted
    while it is active.  Deactivate it first.
    """
    result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.id == contract_id,
            FairnessContract.project_id == project_id,
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        )
    if contract.is_current:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete the currently active contract. Deactivate it first.",
        )
    await db.delete(contract)
    await db.flush()
