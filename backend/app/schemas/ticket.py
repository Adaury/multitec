from datetime import datetime

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    problem: str = Field(max_length=5000)
    technician_id: int | None = None


class TicketUpdate(BaseModel):
    solution: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, max_length=30)
    technician_id: int | None = None


class TicketOut(BaseModel):
    id: int
    code: str
    project_id: int
    technician_id: int | None
    problem: str
    solution: str | None
    status: str
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class TicketHistoryOut(BaseModel):
    id: int
    action: str
    note: str | None
    created_at: datetime

    class Config:
        from_attributes = True
