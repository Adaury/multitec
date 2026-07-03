from datetime import date, datetime, time

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    project_id: int
    technician_id: int | None = None
    scheduled_date: date
    scheduled_time: time | None = None
    notes: str | None = Field(default=None, max_length=2000)


class VisitUpdate(BaseModel):
    technician_id: int | None = None
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    notes: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, max_length=20)


class VisitOut(BaseModel):
    id: int
    project_id: int
    project_code: str
    client_name: str
    technician_id: int | None
    technician_name: str | None = None
    scheduled_date: date
    scheduled_time: time | None
    notes: str | None
    status: str
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
