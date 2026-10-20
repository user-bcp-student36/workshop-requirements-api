from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RequirementUploadResponse(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int = Field(ge=0)
    created_at: datetime