from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Sequence


class Database:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def connect(self) -> None:
        if self._connection is not None:
            return

        if str(self.database_path) != ":memory:":
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(
            str(self.database_path),
            check_same_thread=False,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        self._connection = connection

    def close(self) -> None:
        if self._connection is None:
            return

        self._connection.close()
        self._connection = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Database connection is not initialized.")
        return self._connection

    def execute(self, sql: str, params: Sequence[object] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self.connection.execute(sql, params)

    def executemany(self, sql: str, params: Iterable[Sequence[object]]) -> sqlite3.Cursor:
        with self._lock:
            return self.connection.executemany(sql, params)

    def initialize_schema(self) -> None:
        with self._lock:
            self.connection.executescript(
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
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_created_at_id
                    ON tasks (created_at DESC, id DESC);

                CREATE INDEX IF NOT EXISTS idx_tasks_status
                    ON tasks (status);

                CREATE INDEX IF NOT EXISTS idx_tasks_owner
                    ON tasks (owner);
                """
            )