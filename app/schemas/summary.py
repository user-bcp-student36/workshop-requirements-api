from __future__ import annotations

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]