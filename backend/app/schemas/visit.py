from datetime import date, datetime, time

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    project_id: int
    technician_id: int | None = None
    scheduled_date: date
    scheduled_time: time | None = None
    duration_min: int | None = Field(default=None, ge=5, le=1440)
    notes: str | None = Field(default=None, max_length=2000)


class VisitUpdate(BaseModel):
    technician_id: int | None = None
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    duration_min: int | None = Field(default=None, ge=5, le=1440)
    notes: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, max_length=20)


class VisitPunch(BaseModel):
    """Marcar entrada o salida. Las coordenadas son opcionales: sin GPS o sin permiso la hora igual queda."""

    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class VisitOut(BaseModel):
    id: int
    project_id: int
    project_code: str
    client_name: str
    # Para "Cómo llegar" / "Llamar" directo desde la tarjeta de la visita (calendario).
    client_address: str | None = None
    client_location_url: str | None = None
    client_phone: str | None = None
    technician_id: int | None
    technician_name: str | None = None
    scheduled_date: date
    scheduled_time: time | None
    duration_min: int | None = None
    notes: str | None
    status: str
    checkin_at: datetime | None = None
    checkin_lat: float | None = None
    checkin_lng: float | None = None
    checkout_at: datetime | None = None
    checkout_lat: float | None = None
    checkout_lng: float | None = None
    minutes_on_site: int | None = None
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
