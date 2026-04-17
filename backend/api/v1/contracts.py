"""Fairness contract CRUD endpoints."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from core.schemas import ContractCreate, ContractResponse
from models.db import FairnessContract, Project, User

router = APIRouter(tags=["contracts"])


@router.post(
    "/projects/{project_id}/contracts",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contract(
    project_id: uuid.UUID,
    contract_in: ContractCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new fairness contract for a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    contract_dict = {
        "version": contract_in.version,
        "description": contract_in.description,
        "rules": [r.model_dump() for r in contract_in.rules],
    }
    contract = FairnessContract(
        project_id=project_id,
        version=contract_in.version,
        contract_json=contract_dict,
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return contract


@router.get("/projects/{project_id}/contracts", response_model=list[ContractResponse])
async def list_contracts(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contracts for a project (with history)."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(FairnessContract)
        .where(FairnessContract.project_id == project_id)
        .order_by(FairnessContract.created_at.desc())
    )
    return result.scalars().all()


@router.get("/projects/{project_id}/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific contract."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(FairnessContract).where(
            FairnessContract.id == contract_id,
            FairnessContract.project_id == project_id,
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract
