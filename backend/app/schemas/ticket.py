from datetime import datetime

from pydantic import BaseModel


class TicketCreate(BaseModel):
    problem: str
    technician_id: int | None = None


class TicketUpdate(BaseModel):
    solution: str | None = None
    status: str | None = None
    technician_id: int | None = None


class TicketOut(BaseModel):
    id: int
    code: str
    project_id: int
    technician_id: int | None
    problem: str
    solution: str | None
    status: str
    created_at: datetime
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
