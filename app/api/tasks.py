from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_current_identity, get_tasks_service
from app.models import TaskCreate, TaskPriority, TaskResponse, TaskStatus
from app.security import Identity
from app.services.tasks_service import TasksService


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = Query(default=None),
    owner: str | None = Query(default=None, min_length=1, max_length=120),
    _: Identity = Depends(get_current_identity),
    service: TasksService = Depends(get_tasks_service),
) -> list[TaskResponse]:
    return service.list_tasks(status=task_status, priority=priority, owner=owner)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    identity: Identity = Depends(get_current_identity),
    service: TasksService = Depends(get_tasks_service),
) -> TaskResponse:
    return service.create_task(payload, owner=identity.username)