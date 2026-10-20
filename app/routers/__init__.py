from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_current_principal, get_db
from app.models import TaskCreate, TaskResponse, TaskUpdate, UserPrincipal
from app.repositories import TaskRepository
from app.services import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    principal: Annotated[UserPrincipal, Depends(get_current_principal)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> list[dict[str, object]]:
    return TaskService(TaskRepository(connection)).list_tasks(principal)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    principal: Annotated[UserPrincipal, Depends(get_current_principal)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict[str, object]:
    return TaskService(TaskRepository(connection)).create_task(payload, principal)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    principal: Annotated[UserPrincipal, Depends(get_current_principal)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict[str, object]:
    return TaskService(TaskRepository(connection)).get_task(task_id, principal)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    principal: Annotated[UserPrincipal, Depends(get_current_principal)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict[str, object]:
    return TaskService(TaskRepository(connection)).update_task(task_id, payload, principal)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    principal: Annotated[UserPrincipal, Depends(get_current_principal)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> Response:
    TaskService(TaskRepository(connection)).delete_task(task_id, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)