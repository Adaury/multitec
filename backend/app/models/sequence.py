from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.tenant import TenantMixin


class CodeSequence(TenantMixin, Base):
    """Último correlativo usado por prefijo (PRY, CAM, NVR, CAB, SW...), llevado por empresa: cada empresa numera
    sus propios proyectos, cotizaciones y facturas desde 1."""

    __tablename__ = "code_sequences"

    # La clave es (empresa, prefijo): dos empresas pueden tener "PRY" sin pisarse.
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
