from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import Database


class TasksRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def count_tasks(self) -> int:
        row = self.db.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()
        return int(row["total"])

    def list_tasks(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT id, title, description, status, priority, owner, created_at, updated_at
            FROM tasks
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_task(
        self,
        *,
        title: str,
        description: str,
        status: str,
        priority: str,
        owner: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        cursor = self.db.execute(
            """
            INSERT INTO tasks (title, description, status, priority, owner, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, status, priority, owner, now, now),
        )

        task_id = int(cursor.lastrowid)
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> dict[str, Any]:
        row = self.db.execute(
            """
            SELECT id, title, description, status, priority, owner, created_at, updated_at
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

        if row is None:
            raise KeyError(f"Task {task_id} not found.")

        return dict(row)

    def summary(self) -> dict[str, Any]:
        total = self.count_tasks()

        by_status_rows = self.db.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM tasks
            GROUP BY status
            """
        ).fetchall()

        by_priority_rows = self.db.execute(
            """
            SELECT priority, COUNT(*) AS total
            FROM tasks
            GROUP BY priority
            """
        ).fetchall()

        return {
            "total": total,
            "by_status": {row["status"]: int(row["total"]) for row in by_status_rows},
            "by_priority": {row["priority"]: int(row["total"]) for row in by_priority_rows},
        }