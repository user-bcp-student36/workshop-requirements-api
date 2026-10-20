from __future__ import annotations

from fastapi import HTTPException, status

from app.repositories.tasks_repository import TasksRepository
from app.schemas.tasks import TaskCreate, TaskListResponse, TaskResponse, TaskSummaryResponse, TaskUpdate
from app.security import Identity, raise_forbidden


class TasksService:
    def __init__(self, repository: TasksRepository) -> None:
        self.repository = repository

    def _owner_filter(self, identity: Identity) -> str | None:
        # Admin puede consultar el backlog completo; usuarios solo su propio scope.
        return None if "admin" in identity.roles else identity.subject

    def list_tasks(self, identity: Identity) -> TaskListResponse:
        rows = self.repository.list_tasks(owner=self._owner_filter(identity))
        items = [TaskResponse.model_validate(row) for row in rows]
        return TaskListResponse(items=items, total=len(items))

    def get_task(self, task_id: int, identity: Identity) -> TaskResponse:
        row = self.repository.get_task(task_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._ensure_can_access(row["owner"], identity)
        return TaskResponse.model_validate(row)

    def create_task(self, payload: TaskCreate, identity: Identity) -> TaskResponse:
        row = self.repository.create_task(payload, owner=identity.subject)
        return TaskResponse.model_validate(row)

    def update_task(self, task_id: int, payload: TaskUpdate, identity: Identity) -> TaskResponse:
        existing = self.repository.get_task(task_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._ensure_can_access(existing["owner"], identity)

        row = self.repository.update_task(task_id, payload)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        return TaskResponse.model_validate(row)

    def delete_task(self, task_id: int, identity: Identity) -> None:
        existing = self.repository.get_task(task_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._ensure_can_access(existing["owner"], identity)
        self.repository.delete_task(task_id)

    def summary(self, identity: Identity) -> TaskSummaryResponse:
        data = self.repository.summary(owner=self._owner_filter(identity))
        return TaskSummaryResponse.model_validate(data)

    @staticmethod
    def _ensure_can_access(owner: str, identity: Identity) -> None:
        if "admin" in identity.roles:
            return

        if owner != identity.subject:
            raise_forbidden()