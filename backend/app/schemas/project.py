from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel

from app.schemas.client import ClientOut


class ProjectCreate(BaseModel):
    client_id: int
    responsible_id: int | None = None
    description: str | None = None
    date: date_type | None = None


class ProjectUpdate(BaseModel):
    status: str | None = None
    responsible_id: int | None = None
    description: str | None = None


class ProjectOut(BaseModel):
    id: int
    code: str
    client_id: int
    responsible_id: int | None
    date: date_type
    status: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectDetailOut(ProjectOut):
    client: ClientOut

    class Config:
        from_attributes = True
