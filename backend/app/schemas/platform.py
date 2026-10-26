from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class CompanyCreate(BaseModel):
    """Alta de una empresa nueva junto con su administrador inicial (que entra con una clave temporal)."""

    name: str = Field(min_length=2, max_length=120)
    admin_name: str = Field(min_length=2, max_length=120)
    admin_email: EmailStr
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("admin_email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("name", "admin_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Escribe al menos 2 caracteres")
        return v


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class CompanyOut(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    notes: str | None = None
    created_at: datetime
    users: int = 0
    projects: int = 0
    invoices: int = 0


class CompanyUserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    is_platform_admin: bool = False


class CompanyDetail(CompanyOut):
    team: list[CompanyUserOut] = []
    storage_mb: float = 0


class CompanyCreated(BaseModel):
    company: CompanyOut
    admin_email: str
    # Se muestra una sola vez; el servidor no la guarda en claro.
    temporary_password: str


class ResetAdminRequest(BaseModel):
    user_id: int | None = None  # por defecto, el primer administrador activo de la empresa


class TemporaryPassword(BaseModel):
    user_id: int
    email: str
    temporary_password: str
