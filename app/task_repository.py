from __future__ import annotations

import sqlite3
from threading import RLock

from app.models import Task, TaskCreate

TASK_COLUMNS = "id,title,description,status,owner,priority,created_at"
LIST_TASKS_SQL = f"SELECT {TASK_COLUMNS} FROM tasks WHERE owner=? ORDER BY id"
GET_TASK_SQL = f"SELECT {TASK_COLUMNS} FROM tasks WHERE id=?"
SUMMARY_SQL = "SELECT status,priority FROM tasks WHERE owner=?"
INSERT_TASK_SQL = (
    "INSERT INTO tasks(title,description,status,owner,priority,created_at) "
    "VALUES (?,?,?,?,?,datetime('now'))"
)


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.lock = RLock()

    def list_for_owner(self, owner: str) -> list[Task]:
        with self.lock:
            rows = self.connection.execute(LIST_TASKS_SQL, (owner,)).fetchall()
        return [Task.model_validate(dict(row)) for row in rows]

    def get_by_id(self, task_id: int) -> Task:
        with self.lock:
            row = self.connection.execute(GET_TASK_SQL, (task_id,)).fetchone()
        if row is None:
            raise sqlite3.DatabaseError("Task not found")
        return Task.model_validate(dict(row))

    def create(self, payload: TaskCreate, owner: str) -> Task:
        with self.lock, self.connection:
            cursor = self.connection.execute(INSERT_TASK_SQL, (
                payload.title, payload.description, payload.status, owner, payload.priority,
            ))
            if cursor.lastrowid is None:
                raise sqlite3.DatabaseError("Task identifier not generated")
            return self.get_by_id(cursor.lastrowid)

    def summary_rows(self, owner: str) -> list[sqlite3.Row]:
        with self.lock:
            return self.connection.execute(SUMMARY_SQL, (owner,)).fetchall()