from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(db_path)
    try:
        yield connection
    finally:
        connection.close()


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE')),
                priority TEXT NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
                owner_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        _seed_user(connection, username="alice", role="user")
        _seed_user(connection, username="bob", role="user")
        _seed_user(connection, username="admin", role="admin")


def _seed_user(connection: sqlite3.Connection, *, username: str, role: str) -> None:
    connection.execute(
        """
        INSERT INTO users (username, role)
        VALUES (?, ?)
        ON CONFLICT(username) DO NOTHING
        """,
        (username, role),
    )