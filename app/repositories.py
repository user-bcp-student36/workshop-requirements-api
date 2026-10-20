from __future__ import annotations

import sqlite3
from typing import Any

from app.models import TaskCreate, TaskUpdate, UserPrincipal, UserRole


class UserRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_username(self, username: str) -> UserPrincipal | None:
        row = self._connection.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if row is None:
            return None

        return UserPrincipal(
            id=int(row["id"]),
            username=str(row["username"]),
            role=UserRole(str(row["role"])),
        )


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_for_user(self, principal: UserPrincipal) -> list[dict[str, Any]]:
        if principal.is_admin:
            rows = self._connection.execute(
                """
                SELECT t.id,
                       t.title,
                       t.description,
                       t.status,
                       t.priority,
                       t.owner_id,
                       u.username AS owner_username,
                       t.created_at,
                       t.updated_at
                FROM tasks t
                INNER JOIN users u ON u.id = t.owner_id
                ORDER BY t.id
                """
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT t.id,
                       t.title,
                       t.description,
                       t.status,
                       t.priority,
                       t.owner_id,
                       u.username AS owner_username,
                       t.created_at,
                       t.updated_at
                FROM tasks t
                INNER JOIN users u ON u.id = t.owner_id
                WHERE t.owner_id = ?
                ORDER BY t.id
                """,
                (principal.id,),
            ).fetchall()

        return [_row_to_dict(row) for row in rows]

    def create(self, payload: TaskCreate, owner: UserPrincipal) -> dict[str, Any]:
        cursor = self._connection.execute(
            """
            INSERT INTO tasks (title, description, status, priority, owner_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.title,
                payload.description,
                payload.status.value,
                payload.priority.value,
                owner.id,
            ),
        )
        self._connection.commit()
        return self.get_by_id(int(cursor.lastrowid)) or {}

    def get_by_id(self, task_id: int) -> dict[str, Any] | None:
        row = self._connection.execute(
            """
            SELECT t.id,
                   t.title,
                   t.description,
                   t.status,
                   t.priority,
                   t.owner_id,
                   u.username AS owner_username,
                   t.created_at,
                   t.updated_at
            FROM tasks t
            INNER JOIN users u ON u.id = t.owner_id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_dict(row)

    def update(self, task_id: int, payload: TaskUpdate) -> dict[str, Any] | None:
        existing = self.get_by_id(task_id)
        if existing is None:
            return None

        self._connection.execute(
            """
            UPDATE tasks
            SET title = ?,
                description = ?,
                status = ?,
                priority = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                payload.title if payload.title is not None else existing["title"],
                payload.description
                if payload.description is not None
                else existing["description"],
                payload.status.value if payload.status is not None else existing["status"],
                payload.priority.value
                if payload.priority is not None
                else existing["priority"],
                task_id,
            ),
        )
        self._connection.commit()
        return self.get_by_id(task_id)

    def delete(self, task_id: int) -> bool:
        cursor = self._connection.execute(
            """
            DELETE FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        self._connection.commit()
        return cursor.rowcount > 0


class UploadRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(
        self,
        *,
        task_id: int,
        owner_id: int,
        original_filename: str,
        stored_filename: str,
        content_type: str,
        size_bytes: int,
    ) -> dict[str, Any]:
        cursor = self._connection.execute(
            """
            INSERT INTO uploads (
                task_id,
                owner_id,
                original_filename,
                stored_filename,
                content_type,
                size_bytes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                owner_id,
                original_filename,
                stored_filename,
                content_type,
                size_bytes,
            ),
        )
        self._connection.commit()
        return self.get_by_id(int(cursor.lastrowid)) or {}

    def get_by_id(self, upload_id: int) -> dict[str, Any] | None:
        row = self._connection.execute(
            """
            SELECT id,
                   task_id,
                   owner_id,
                   original_filename,
                   stored_filename,
                   content_type,
                   size_bytes,
                   created_at
            FROM uploads
            WHERE id = ?
            """,
            (upload_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_dict(row)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}