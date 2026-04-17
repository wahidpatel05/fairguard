"""API endpoints for audit report generation (PDF and Markdown)."""
from __future__ import annotations

import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_either
from app.models.audit import OfflineAudit
from app.models.contract import FairnessContract
from app.models.project import Project
from app.models.user import User
from app.services.fairness import FairnessEngine
from app.services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_audit_and_context(
    audit_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> tuple[OfflineAudit, Project, list[dict], list[dict]]:
    """Shared helper: fetch audit, verify access, re-evaluate contracts."""
    audit_result = await db.execute(
        select(OfflineAudit).where(OfflineAudit.id == audit_id)
    )
    audit = audit_result.scalar_one_or_none()
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

    # Re-evaluate contracts from stored metrics
    contract_results: list[dict] = []
    if audit.metrics_json is not None:
        contract_row = await db.execute(
            select(FairnessContract).where(
                FairnessContract.project_id == audit.project_id,
                FairnessContract.is_current == True,  # noqa: E712
            )
        )
        current_contract = contract_row.scalar_one_or_none()
        if current_contract is not None:
            contract_results = FairnessEngine.evaluate_contracts(
                audit.metrics_json, current_contract.contracts_json
            )

    failing = [r for r in contract_results if not r.get("passed", True)]
    recommendations = FairnessEngine.generate_mitigation_recommendations(failing)

    return audit, project, contract_results, recommendations


# ---------------------------------------------------------------------------
# GET /reports/{audit_id}/pdf
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/pdf")
async def get_audit_pdf(
    audit_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Generate and stream a PDF audit report."""
    audit, project, contract_results, recommendations = await _get_audit_and_context(
        audit_id, current_user, db
    )

    audit_dict = {
        "id": str(audit.id),
        "verdict": audit.verdict,
        "created_at": str(audit.created_at),
        "dataset_hash": audit.dataset_hash,
        "dataset_filename": audit.dataset_filename,
    }
    project_dict = {
        "id": str(project.id),
        "name": project.name,
        "domain": project.domain,
    }

    pdf_bytes = ReportService.generate_pdf(
        audit=audit_dict,
        project=project_dict,
        contract_results=contract_results,
        metrics=audit.metrics_json or {},
        recommendations=recommendations,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=audit_{audit_id}.pdf"
        },
    )


# ---------------------------------------------------------------------------
# GET /reports/{audit_id}/markdown
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/markdown")
async def get_audit_markdown(
    audit_id: UUID,
    current_user: User = Depends(get_current_user_either),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and return a Markdown audit report."""
    audit, project, contract_results, recommendations = await _get_audit_and_context(
        audit_id, current_user, db
    )

    audit_dict = {
        "id": str(audit.id),
        "verdict": audit.verdict,
        "created_at": str(audit.created_at),
        "dataset_hash": audit.dataset_hash,
        "dataset_filename": audit.dataset_filename,
    }
    project_dict = {
        "id": str(project.id),
        "name": project.name,
        "domain": project.domain,
    }

    md_string = ReportService.generate_markdown(
        audit=audit_dict,
        project=project_dict,
        contract_results=contract_results,
        metrics=audit.metrics_json or {},
        recommendations=recommendations,
    )

    return Response(
        content=md_string,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=audit_{audit_id}.md"
        },
    )
