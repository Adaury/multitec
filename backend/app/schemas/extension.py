from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field


class ExtensionCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    quote_id: int | None = None
    date: date_type | None = None


class ExtensionStatusUpdate(BaseModel):
    status: str = Field(max_length=30)


class ExtensionOut(BaseModel):
    id: int
    code: str
    project_id: int
    quote_id: int | None
    title: str
    description: str | None
    status: str
    date: date_type
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
