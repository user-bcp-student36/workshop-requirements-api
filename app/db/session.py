from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

from app.core.config import Settings


def create_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database(settings: Settings) -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)

    connection = create_connection(settings.db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                owner TEXT NOT NULL,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")
        connection.commit()
    finally:
        connection.close()


def get_connection(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    connection = create_connection(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()