from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.tasks import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


class TasksRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        if self.database_path.parent != Path("."):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize_schema(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_owner
                ON tasks(owner)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks(status)
                """
            )

    def list_tasks(self, *, owner: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, title, description, status, priority, owner, created_at, updated_at
            FROM tasks
        """
        params: tuple[Any, ...] = ()

        if owner is not None:
            query += " WHERE owner = ?"
            params = (owner,)

        query += " ORDER BY id ASC"

        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, title, description, status, priority, owner, created_at, updated_at
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()

        return dict(row) if row else None

    def create_task(self, task: TaskCreate, *, owner: str) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()

        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks(title, description, status, priority, owner, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority.value,
                    owner,
                    now,
                    now,
                ),
            )
            task_id = int(cursor.lastrowid)

        created = self.get_task(task_id)
        if created is None:
            raise RuntimeError("created task could not be loaded")

        return created

    def update_task(self, task_id: int, update: TaskUpdate) -> dict[str, Any] | None:
        values = update.model_dump(exclude_unset=True)
        if not values:
            return self.get_task(task_id)

        allowed_columns = {"title", "description", "status", "priority"}
        assignments: list[str] = []
        params: list[Any] = []

        for column, value in values.items():
            if column not in allowed_columns:
                continue

            assignments.append(f"{column} = ?")
            if isinstance(value, TaskStatus | TaskPriority):
                params.append(value.value)
            else:
                params.append(value)

        if not assignments:
            return self.get_task(task_id)

        assignments.append("updated_at = ?")
        params.append(datetime.now(UTC).isoformat())
        params.append(task_id)

        with self._connection() as connection:
            connection.execute(
                f"""
                UPDATE tasks
                SET {", ".join(assignments)}
                WHERE id = ?
                """,
                tuple(params),
            )

        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,),
            )

        return cursor.rowcount > 0

    def summary(self, *, owner: str | None = None) -> dict[str, Any]:
        where_clause = ""
        params: tuple[Any, ...] = ()

        if owner is not None:
            where_clause = "WHERE owner = ?"
            params = (owner,)

        with self._connection() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM tasks {where_clause}",
                    params,
                ).fetchone()[0]
            )

            status_rows = connection.execute(
                f"""
                SELECT status, COUNT(*) AS count
                FROM tasks
                {where_clause}
                GROUP BY status
                """,
                params,
            ).fetchall()

            priority_rows = connection.execute(
                f"""
                SELECT priority, COUNT(*) AS count
                FROM tasks
                {where_clause}
                GROUP BY priority
                """,
                params,
            ).fetchall()

        by_status = {status: 0 for status in TaskStatus}
        for row in status_rows:
            by_status[TaskStatus(row["status"])] = int(row["count"])

        by_priority = {priority: 0 for priority in TaskPriority}
        for row in priority_rows:
            by_priority[TaskPriority(row["priority"])] = int(row["count"])

        return {
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
        }