from datetime import date, datetime

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
    # Tarifas propias de esta empresa (RD$); clear_fees vuelve a la tarifa general.
    setup_fee: float | None = Field(default=None, ge=0, le=10_000_000)
    monthly_fee: float | None = Field(default=None, ge=0, le=10_000_000)
    clear_fees: bool = False
    # Corregir a mano «pagado hasta» (p. ej. un pago anotado por error).
    paid_until: date | None = None
    contact_phone: str | None = Field(default=None, max_length=30)
    # Cambiar de plan (también ajusta el tope de usuarios al del plan).
    plan_id: int | None = None


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
    # activa | prueba | vencida | atrasada | cortada | suspendida
    state: str = "activa"
    source: str = "panel"
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    setup_fee: float = 0
    monthly_fee: float = 0
    setup_paid_at: datetime | None = None
    paid_until: datetime | None = None
    reviewed_at: datetime | None = None
    plan_id: int | None = None
    plan_name: str | None = None
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


class PaymentOut(BaseModel):
    id: int
    kind: str
    amount: float
    months: int
    method: str
    reference: str | None = None
    notes: str | None = None
    paid_at: date
    paid_until_after: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CompanyDetail(CompanyOut):
    team: list[CompanyUserOut] = []
    storage_mb: float = 0
    payments: list[PaymentOut] = []


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


class PaymentCreate(BaseModel):
    """Un pago recibido de una empresa (lo anota la plataforma)."""

    kind: str = Field(pattern="^(instalacion|mensualidad)$")
    amount: float = Field(gt=0, le=10_000_000)
    # Meses de servicio que cubre: la mensualidad normalmente 1; la instalación puede incluir el primer mes (1) o no (0).
    months: int = Field(default=1, ge=0, le=36)
    method: str = Field(pattern="^(transferencia|deposito|efectivo|tarjeta|otro)$")
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    paid_at: date | None = None  # vacío = hoy


class SupportSessionCreate(BaseModel):
    allow_changes: bool = False


class SupportSession(BaseModel):
    access_token: str
    company_id: int
    company_name: str
    allow_changes: bool
    expires_at: datetime


class SignupRequest(BaseModel):
    """Registro público de una empresa nueva (página /registro)."""

    company_name: str = Field(min_length=2, max_length=120)
    admin_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    password: str = Field(min_length=1, max_length=255)
    accept_terms: bool
    plan_id: int | None = None
    # Trampa para robots: un campo oculto que una persona nunca llena.
    website: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("company_name", "admin_name", "phone")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Escribe al menos 2 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return check_password_policy(v)


class SignupDone(BaseModel):
    company_name: str
    email: str
    trial_days: int
    trial_ends_at: datetime


class SubscriptionOut(BaseModel):
    """«Mi suscripción» del administrador de una empresa."""

    company_name: str
    state: str
    trial_ends_at: datetime | None = None
    paid_until: datetime | None = None
    days_left: int | None = None
    setup_fee: float
    monthly_fee: float
    setup_paid: bool
    notice: str | None = None
    payment_info: str = ""
    contact_phone: str = ""
    contact_phones: list[str] = []
    plan_name: str | None = None
    currency: str = "USD"
    payments: list[PaymentOut] = []
