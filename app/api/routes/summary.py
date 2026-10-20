from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_tasks_service, require_permissions
from app.schemas import SummaryRead
from app.services.tasks_service import TasksService


router = APIRouter(prefix="/summary", tags=["summary"])


@router.get(
    "",
    response_model=SummaryRead,
    dependencies=[Depends(require_permissions("summary:read"))],
)
def get_summary(service: TasksService = Depends(get_tasks_service)) -> SummaryRead:
    return service.summary()