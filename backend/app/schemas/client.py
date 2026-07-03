from datetime import datetime

from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    name: str = Field(max_length=150)
    company: str | None = Field(default=None, max_length=150)
    rnc: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    pass


class ClientOut(ClientBase):
    id: int
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
