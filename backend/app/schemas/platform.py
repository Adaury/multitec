from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import check_password_policy


class CompanyCreate(BaseModel):
    """Alta de una empresa nueva junto con su administrador inicial (que entra con una clave temporal)."""

    name: str = Field(min_length=2, max_length=120)
    admin_name: str = Field(min_length=2, max_length=120)
    admin_email: EmailStr
    notes: str | None = Field(default=None, max_length=2000)
    # Días de prueba desde hoy; vacío = sin vencimiento (empresa que ya paga).
    trial_days: int | None = Field(default=None, ge=1, le=365)
    # Tope de usuarios activos; vacío = sin tope.
    max_users: int | None = Field(default=None, ge=1, le=1000)

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
    # Alarga la prueba N días: desde hoy si ya venció, o desde su fecha de vencimiento si sigue vigente.
    extend_days: int | None = Field(default=None, ge=1, le=365)
    # True quita el vencimiento (pasa a ser cliente sin prueba).
    clear_trial: bool = False
    max_users: int | None = Field(default=None, ge=1, le=1000)
    clear_max_users: bool = False


class CompanyOut(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    notes: str | None = None
    created_at: datetime
    trial_ends_at: datetime | None = None
    days_left: int | None = None  # negativo = venció hace N días
    max_users: int | None = None
    is_demo: bool = False
    # activa | prueba | vencida | suspendida
    state: str = "activa"
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
    admin_user_id: int
    # Se muestra una sola vez; el servidor no la guarda en claro.
    temporary_password: str


class ResetAdminRequest(BaseModel):
    user_id: int | None = None  # por defecto, el primer administrador activo de la empresa


class TemporaryPassword(BaseModel):
    user_id: int
    email: str
    temporary_password: str


class DemoCreate(BaseModel):
    """Empresa de demostración para que los técnicos prueben la app un tiempo."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    technicians: int = Field(default=3, ge=1, le=10)
    days: int = Field(default=14, ge=1, le=90)


class DemoAccount(BaseModel):
    user_id: int
    name: str
    email: str
    role: str
    temporary_password: str


class DemoCreated(BaseModel):
    company: CompanyOut
    accounts: list[DemoAccount]


class SetUserPassword(BaseModel):
    """Clave nueva para un usuario de una empresa. Vacía = el servidor genera una al azar."""

    password: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def _policy(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return check_password_policy(v) if v else None
