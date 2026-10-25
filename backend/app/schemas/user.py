from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Role = Literal["admin", "oficina", "tecnico"]

# bcrypt (ver core/security.py::hash_password) trunca/falla más allá de 72 bytes — se
# valida acá para dar un 422 claro en vez de que hash_password truene con un 500.
_MAX_PASSWORD_BYTES = 72


MIN_PASSWORD_LENGTH = 10

# Claves que cualquiera prueba primero (NIST 800-63B: rechazar las comunes, no imponer mayúsculas ni símbolos).
_COMMON_PASSWORDS = frozenset(
    """
    1234567890 0123456789 12345678910 1q2w3e4r5t qwertyuiop asdfghjkl password1 password12 password123
    passw0rd123 contrasena contrasena1 contrasena12 contrasena123 contraseña contraseña1 contraseña123
    admin12345 administrador administrator1 multitec123 multitec1234 multitec2026 multitec2025
    change-this-password cambiar123 iloveyou12 letmein123 welcome123 welcome1234 bienvenido1 bienvenido123
    abc1234567 abcd123456 qwerty1234 qwerty12345 qwerty123456 123456789a a123456789 1234567890a
    santodomingo republicadominicana dominicana1 dominicana123
    """.split()
)


def check_password_policy(password: str) -> str:
    """Política para claves nuevas (no afecta a las ya guardadas): largo mínimo, nada de claves comunes
    ni de un solo carácter o solo dígitos, y el límite de bytes de bcrypt."""
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise ValueError(f"La contraseña no puede superar los {_MAX_PASSWORD_BYTES} bytes")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS or password.isdigit() or len(set(password)) == 1:
        raise ValueError("Esa contraseña es demasiado común. Elige una que no sea fácil de adivinar")
    return password


# Nombre antiguo, lo usan otros esquemas.
_check_password_bcrypt_length = check_password_policy


class UserCreate(BaseModel):
    name: str = Field(max_length=120)
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=255)
    role: Role = "oficina"
    # Ficha del miembro del equipo (todo opcional).
    phone: str | None = Field(default=None, max_length=30)
    zone: str | None = Field(default=None, max_length=80)
    skills: str | None = Field(default=None, max_length=255)
    vehicle: str | None = Field(default=None, max_length=80)

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
    # El correo es con lo que la persona entra: si cambia el nombre, el admin puede ajustarlo también.
    email: EmailStr | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=MIN_PASSWORD_LENGTH, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    zone: str | None = Field(default=None, max_length=80)
    skills: str | None = Field(default=None, max_length=255)
    vehicle: str | None = Field(default=None, max_length=80)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str | None) -> str | None:
        # Misma normalización que al crear: el correo siempre en minúsculas (ver UserCreate).
        return v.lower() if v else v

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
    phone: str | None = None
    zone: str | None = None
    skills: str | None = None
    vehicle: str | None = None
    last_login_at: datetime | None = None
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    """Una sesión abierta (un dispositivo con la app iniciada)."""

    id: int
    created_at: datetime
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip: str | None = None
    current: bool = False

    class Config:
        from_attributes = True


class TemporaryPasswordOut(BaseModel):
    temporary_password: str


class WorkloadOut(BaseModel):
    user_id: int
    name: str
    visits_total: int
    visits_pending: int
    visits_done: int
    open_tickets: int
    hours_on_site: float


class TechnicianOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
