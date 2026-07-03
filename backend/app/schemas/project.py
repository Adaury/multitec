from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.client import ClientOut


class ProjectCreate(BaseModel):
    client_id: int
    responsible_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    date: date_type | None = None


class ProjectUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=30)
    responsible_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)


class ProjectOut(BaseModel):
    id: int
    code: str
    client_id: int
    responsible_id: int | None
    date: date_type
    status: str
    description: str | None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ProjectDetailOut(ProjectOut):
    client: ClientOut

    class Config:
        from_attributes = True
