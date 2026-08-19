from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Role = Literal["admin", "oficina", "tecnico"]

# bcrypt (ver core/security.py::hash_password) trunca/falla más allá de 72 bytes — se
# valida acá para dar un 422 claro en vez de que hash_password truene con un 500.
_MAX_PASSWORD_BYTES = 72


def _check_password_bcrypt_length(password: str) -> str:
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise ValueError(f"La contraseña no puede superar los {_MAX_PASSWORD_BYTES} bytes")
    return password


class UserCreate(BaseModel):
    name: str = Field(max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    role: Role = "oficina"

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        # Sin esto, "Admin@x.com" y "admin@x.com" pasan la restricción unique como
        # cuentas distintas (case-sensitive a nivel de columna) — se normaliza a
        # minúsculas para que el correo sea el mismo identificador sin importar cómo se
        # haya tecleado. login (auth.py) hace la misma normalización al comparar.
        return v.lower()

    @field_validator("password")
    @classmethod
    def _check_password_length(cls, v: str) -> str:
        return _check_password_bcrypt_length(v)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=255)

    @field_validator("password")
    @classmethod
    def _check_password_length(cls, v: str | None) -> str | None:
        return _check_password_bcrypt_length(v) if v else v


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


class TechnicianOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
