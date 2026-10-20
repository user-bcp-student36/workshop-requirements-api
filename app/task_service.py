from __future__ import annotations

from collections import Counter
from http import HTTPStatus

from fastapi import HTTPException

from app.models import CLOSED_STATUSES, HIGH_PRIORITY, Identity, Task, TaskCreate, TaskSummary
from app.task_repository import TaskRepository

OWNER_MISMATCH_DETAIL = "Owner does not match authenticated identity"


def authorized_owner(requested_owner: str | None, identity: Identity) -> str:
    if requested_owner is not None and requested_owner != identity.username:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=OWNER_MISMATCH_DETAIL)
    return identity.username


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def list_tasks(self, owner: str | None, identity: Identity) -> list[Task]:
        authenticated_owner = authorized_owner(owner or None, identity)
        return self.repository.list_for_owner(authenticated_owner)

    def create_task(self, payload: TaskCreate, identity: Identity) -> Task:
        authenticated_owner = authorized_owner(payload.owner, identity)
        return self.repository.create(payload, authenticated_owner)

    def summary(self, owner: str | None, identity: Identity) -> TaskSummary:
        authenticated_owner = authorized_owner(owner or None, identity)
        rows = self.repository.summary_rows(authenticated_owner)
        return TaskSummary(
            owner=authenticated_owner,
            total=len(rows),
            by_status=dict(Counter(row["status"] for row in rows)),
            high_priority_open=sum(
                row["priority"] == HIGH_PRIORITY and row["status"] not in CLOSED_STATUSES
                for row in rows
            ),
        )