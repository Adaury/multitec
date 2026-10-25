from datetime import date, datetime

from pydantic import BaseModel


class TimesheetRow(BaseModel):
    visit_id: int
    date: date
    technician_id: int | None
    technician: str
    project_code: str
    client_name: str
    checkin_at: datetime
    checkout_at: datetime | None
    # None mientras falte la salida: la visita sigue en curso o se olvidó marcar.
    minutes: int | None


class TimesheetTotal(BaseModel):
    technician_id: int | None
    technician: str
    visits: int
    minutes: int
    open: int


class TimesheetOut(BaseModel):
    start: date
    end: date
    rows: list[TimesheetRow]
    totals: list[TimesheetTotal]
