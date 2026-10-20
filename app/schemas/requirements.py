from __future__ import annotations

from pydantic import BaseModel


class RequirementUploadResponse(BaseModel):
    filename: str
    size: int