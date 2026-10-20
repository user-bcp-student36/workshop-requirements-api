from __future__ import annotations

from app.repositories.tasks_repository import TasksRepository


def seed_demo_data(repository: TasksRepository) -> None:
    # Seed separado del lifecycle: sólo se ejecuta si la configuración lo habilita explícitamente.
    if repository.count_tasks() > 0:
        return

    repository.create_task(
        title="Review requirements",
        description="Read uploaded requirements and identify missing cases.",
        status="TODO",
        priority="MEDIUM",
        owner="demo",
    )
    repository.create_task(
        title="Design API contract",
        description="Define endpoints, payloads and authorization requirements.",
        status="IN_PROGRESS",
        priority="HIGH",
        owner="demo",
    )