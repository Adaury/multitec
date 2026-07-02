from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel


class ExtensionCreate(BaseModel):
    title: str
    description: str | None = None
    quote_id: int | None = None
    date: date_type | None = None


class ExtensionStatusUpdate(BaseModel):
    status: str


class ExtensionOut(BaseModel):
    id: int
    code: str
    project_id: int
    quote_id: int | None
    title: str
    description: str | None
    status: str
    date: date_type
    created_at: datetime

    class Config:
        from_attributes = True
