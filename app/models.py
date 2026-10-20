from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    description: str
    status: str
    priority: str
    owner: str