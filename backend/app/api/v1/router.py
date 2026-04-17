from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.audits import router as audits_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.projects import router as projects_router
from app.api.v1.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(api_keys_router)
api_router.include_router(audits_router)
api_router.include_router(contracts_router)
api_router.include_router(projects_router)
api_router.include_router(users_router)

# Stubs for agents 4-7 (routers will be provided by later agents)
# api_router.include_router(runtime_router)
# api_router.include_router(receipts_router)
# api_router.include_router(reports_router)
# api_router.include_router(notifications_router)
