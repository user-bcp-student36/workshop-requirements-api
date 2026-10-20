from __future__ import annotations

from app.repositories.tasks_repository import TasksRepository
from app.schemas import SummaryRead, TaskCreate, TaskPage, TaskRead


class TasksService:
    def __init__(self, repository: TasksRepository) -> None:
        self.repository = repository

    def list_tasks(self, *, limit: int, offset: int) -> TaskPage:
        return TaskPage(
            items=[TaskRead(**row) for row in self.repository.list_tasks(limit=limit, offset=offset)],
            total=self.repository.count_tasks(),
            limit=limit,
            offset=offset,
        )

    def create_task(self, payload: TaskCreate, *, owner: str) -> TaskRead:
        row = self.repository.create_task(
            title=payload.title.strip(),
            description=payload.description.strip(),
            status=payload.status.value,
            priority=payload.priority.value,
            owner=owner,
        )
        return TaskRead(**row)

    def summary(self) -> SummaryRead:
        return SummaryRead(**self.repository.summary())