from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import MIN_PASSWORD_LENGTH, check_password_policy


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # Opcional: el navegador lo manda en la cookie HttpOnly; el cuerpo se conserva para clientes
    # sin cookies (pruebas, scripts) y para migrar sesiones que aún lo tienen en localStorage.
    refresh_token: str | None = None


class CurrentUser(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    assistant_alias: str | None = None
    must_change_password: bool = False

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    # Si no viene en la petición no se toca; si viene vacío se borra (vuelve al nombre por defecto).
    assistant_alias: str | None = Field(default=None, max_length=60)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("assistant_alias")
    @classmethod
    def _strip_alias(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=255)

    @field_validator("new_password")
    @classmethod
    def _check_new_password_policy(cls, v: str) -> str:
        return check_password_policy(v)
