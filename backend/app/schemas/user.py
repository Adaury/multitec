from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["admin", "oficina", "tecnico"]


class UserCreate(BaseModel):
    name: str = Field(max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    role: Role = "oficina"


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=255)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
