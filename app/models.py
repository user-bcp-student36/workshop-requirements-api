from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class UserRole(StrEnum):
    user = "user"
    admin = "admin"


class TaskStatus(StrEnum):
    todo = "TODO"
    in_progress = "IN_PROGRESS"
    done = "DONE"


class TaskPriority(StrEnum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"


class UserPrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    username: str
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.admin


class TokenClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: str
    role: UserRole
    exp: int


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(min_length=1, max_length=2_000)]
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    description: Annotated[str | None, Field(min_length=1, max_length=2_000)] = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    owner_id: int
    owner_username: str
    created_at: str
    updated_at: str


class UploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    task_id: int
    owner_id: int
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    created_at: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str