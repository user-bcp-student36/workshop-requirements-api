from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL UNIQUE,
                    content_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    owner TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            if task_count == 0:
                connection.executemany(
                    """
                    INSERT INTO tasks
                        (title, description, status, priority, owner)
                    VALUES
                        (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            "Review workshop requirements",
                            "Identify backend security and maintainability gaps.",
                            "TODO",
                            "HIGH",
                            "student",
                        ),
                        (
                            "Prepare refactoring plan",
                            "Document target layers, contracts and tests.",
                            "DONE",
                            "MEDIUM",
                            "student",
                        ),
                    ],
                )