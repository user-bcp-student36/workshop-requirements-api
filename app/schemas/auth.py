from __future__ import annotations

from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    role: str = Field(..., min_length=1, max_length=50)