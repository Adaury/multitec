import re
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core.timeutil import today_dr
from app.models.client_asset import ASSET_KINDS

# Garantía que vence en menos de estos días se marca "por vencer": hay tiempo de avisar al cliente.
WARRANTY_SOON_DAYS = 60

_HEX12 = re.compile(r"^[0-9A-F]{12}$")


def _normalize_mac(value: str | None) -> str | None:
    """AA:BB:CC:DD:EE:FF a partir de AA-BB-..., aabb.ccdd.eeff o AABBCCDDEEFF. Vacío = sin MAC."""
    if value is None or not value.strip():
        return None
    digits = re.sub(r"[^0-9A-Fa-f]", "", value).upper()
    if not _HEX12.match(digits):
        raise ValueError("La MAC debe tener 12 dígitos hexadecimales (ej. AA:BB:CC:DD:EE:FF)")
    return ":".join(digits[i : i + 2] for i in range(0, 12, 2))


class _AssetFields(BaseModel):
    kind: str = Field(default="otro", max_length=40)
    name: str = Field(min_length=1, max_length=120)
    brand: str | None = Field(default=None, max_length=60)
    model: str | None = Field(default=None, max_length=60)
    serial: str | None = Field(default=None, max_length=80)
    mac: str | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    location: str | None = Field(default=None, max_length=160)
    installed_on: date | None = None
    warranty_until: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    project_id: int | None = None

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, v: str) -> str:
        if v not in ASSET_KINDS:
            raise ValueError(f"Tipo de equipo inválido: {v}")
        return v

    @field_validator("mac")
    @classmethod
    def _mac(cls, v: str | None) -> str | None:
        return _normalize_mac(v)

    @field_validator("brand", "model", "serial", "ip_address", "location", "notes")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None


class ClientAssetCreate(_AssetFields):
    pass


class ClientAssetUpdate(BaseModel):
    kind: str | None = Field(default=None, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    brand: str | None = Field(default=None, max_length=60)
    model: str | None = Field(default=None, max_length=60)
    serial: str | None = Field(default=None, max_length=80)
    mac: str | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    location: str | None = Field(default=None, max_length=160)
    installed_on: date | None = None
    warranty_until: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    project_id: int | None = None

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, v: str | None) -> str | None:
        if v is not None and v not in ASSET_KINDS:
            raise ValueError(f"Tipo de equipo inválido: {v}")
        return v

    @field_validator("mac")
    @classmethod
    def _mac(cls, v: str | None) -> str | None:
        return _normalize_mac(v)

    @field_validator("brand", "model", "serial", "ip_address", "location", "notes")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None


class ClientAssetOut(BaseModel):
    id: int
    client_id: int
    project_id: int | None
    kind: str
    name: str
    brand: str | None
    model: str | None
    serial: str | None
    mac: str | None
    ip_address: str | None
    location: str | None
    installed_on: date | None
    warranty_until: date | None
    notes: str | None
    created_at: datetime
    # vigente | por_vencer | vencida | None (sin fecha de garantía). Se calcula al responder, no se guarda.
    warranty_status: str | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_row(cls, row) -> "ClientAssetOut":
        out = cls.model_validate(row)
        out.warranty_status = warranty_status(row.warranty_until)
        return out


def warranty_status(until: date | None) -> str | None:
    if until is None:
        return None
    days = (until - today_dr()).days
    if days < 0:
        return "vencida"
    return "por_vencer" if days <= WARRANTY_SOON_DAYS else "vigente"
