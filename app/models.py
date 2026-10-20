from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_TITLE = ""
DEFAULT_DESCRIPTION = ""
DEFAULT_STATUS = "TODO"
DEFAULT_PRIORITY = "MEDIUM"
HIGH_PRIORITY = "HIGH"
CLOSED_STATUSES = frozenset({"DONE", "ARCHIVED"})


class Identity(BaseModel):
    username: str
    role: str


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = DEFAULT_TITLE
    description: str = DEFAULT_DESCRIPTION
    status: str = DEFAULT_STATUS
    priority: str = DEFAULT_PRIORITY
    owner: str | None = None

    @field_validator("title", "description", "status", "priority", "owner", mode="before")
    @classmethod
    def normalize_legacy_value(cls, value: object) -> str:
        return str(value)


class Task(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    created_at: str = Field(alias="createdAt")


class TaskSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    owner: str
    total: int
    by_status: dict[str, int] = Field(alias="byStatus")
    high_priority_open: int = Field(alias="highPriorityOpen")


class UploadResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    owner: str
    file_name: str = Field(alias="fileName")
    stored_at: str = Field(alias="storedAt")
    size: int