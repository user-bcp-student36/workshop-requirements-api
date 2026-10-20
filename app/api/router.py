from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.requirements import router as requirements_router
from app.api.routes.summary import router as summary_router
from app.api.routes.tasks import router as tasks_router

api_router = APIRouter(prefix="/api")

api_router.include_router(tasks_router)
api_router.include_router(requirements_router)
api_router.include_router(summary_router)