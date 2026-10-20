from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_identity, get_tasks_service
from app.models import TaskSummaryResponse
from app.security import Identity
from app.services.tasks_service import TasksService


router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("", response_model=TaskSummaryResponse)
def get_summary(
    _: Identity = Depends(get_current_identity),
    service: TasksService = Depends(get_tasks_service),
) -> TaskSummaryResponse:
    return service.summary()