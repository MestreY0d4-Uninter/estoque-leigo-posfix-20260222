from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    sqlite_path: str


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class NoteOut(BaseModel):
    id: int
    content: str
    created_at: datetime
