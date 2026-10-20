from __future__ import annotations

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    status: str = Field(default="TODO", min_length=1)
    priority: str = Field(default="MEDIUM", min_length=1)


class TaskRead(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    owner: str