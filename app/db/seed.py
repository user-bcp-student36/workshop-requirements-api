from __future__ import annotations

import sqlite3


SEED_TASKS = (
    {
        "title": "Review requirements",
        "description": "Read the provided requirements document",
        "status": "TODO",
        "priority": "MEDIUM",
        "owner": "student",
    },
    {
        "title": "Implement API",
        "description": "Build the backend endpoints",
        "status": "IN_PROGRESS",
        "priority": "HIGH",
        "owner": "student",
    },
)


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            owner TEXT NOT NULL
        )
        """
    )
    connection.commit()


def seed_database(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()
    if int(existing["total"]) > 0:
        return

    connection.executemany(
        """
        INSERT INTO tasks (title, description, status, priority, owner)
        VALUES (:title, :description, :status, :priority, :owner)
        """,
        SEED_TASKS,
    )
    connection.commit()