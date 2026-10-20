from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_tasks_service, require_roles
from app.schemas.tasks import TaskCreate, TaskListResponse, TaskResponse, TaskSummaryResponse, TaskUpdate
from app.security import Identity
from app.services.tasks_service import TasksService


router = APIRouter(prefix="/api", tags=["tasks"])


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
)
def list_tasks(
    identity: Identity = Depends(require_roles("user", "admin")),
    service: TasksService = Depends(get_tasks_service),
) -> TaskListResponse:
    return service.list_tasks(identity)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
def get_task(
    task_id: int,
    identity: Identity = Depends(require_roles("user", "admin")),
    service: TasksService = Depends(get_tasks_service),
) -> TaskResponse:
    return service.get_task(task_id, identity)


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    identity: Identity = Depends(require_roles("user", "admin")),
    service: TasksService = Depends(get_tasks_service),
) -> TaskResponse:
    return service.create_task(payload, identity)


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    identity: Identity = Depends(require_roles("user", "admin")),
    service: TasksService = Depends(get_tasks_service),
) -> TaskResponse:
    return service.update_task(task_id, payload, identity)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: int,
    identity: Identity = Depends(require_roles("user", "admin")),
    service: TasksService = Depends(get_tasks_service),
) -> Response:
    service.delete_task(task_id, identity)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/summary",
    response_model=TaskSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def get_summary(
    identity: Identity = Depends(require_roles("user", "admin")),
    service: TasksService = Depends(get_tasks_service),
) -> TaskSummaryResponse:
    return service.summary(identity)