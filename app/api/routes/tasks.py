from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_tasks_service, require_permissions
from app.schemas import TaskCreate, TaskPage, TaskRead
from app.security import Identity
from app.services.tasks_service import TasksService


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "",
    response_model=TaskPage,
    dependencies=[Depends(require_permissions("tasks:read"))],
)
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: TasksService = Depends(get_tasks_service),
) -> TaskPage:
    return service.list_tasks(limit=limit, offset=offset)


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    identity: Identity = Depends(require_permissions("tasks:create")),
    service: TasksService = Depends(get_tasks_service),
) -> TaskRead:
    return service.create_task(payload, owner=identity.sub)