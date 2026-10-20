from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE"]
TaskPriority = Literal["LOW", "MEDIUM", "HIGH"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TaskCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2_000)
    status: TaskStatus = "TODO"
    priority: TaskPriority = "MEDIUM"


class TaskUpdateRequest(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=2_000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    owner: str


class SummaryResponse(BaseModel):
    total: int
    by_status: dict[str, int]


class UploadResponse(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    owner: str


class ErrorResponse(BaseModel):
    detail: str