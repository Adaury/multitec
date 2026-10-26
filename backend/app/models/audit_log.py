from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.tenant import TenantMixin


class AuditLog(TenantMixin, Base):
    """Quién hizo qué y cuándo (solo se agrega, nunca se edita ni se borra desde la app).

    `user_email` se guarda aparte del `user_id` para que un intento de acceso fallido (sin usuario) o un
    usuario desactivado después sigan siendo identificables. `detail` es un JSON en texto con lo que cambió
    (nunca contraseñas ni tokens)."""

    __tablename__ = "audit_log"

    # Opcional a diferencia de las demás tablas de empresa: un intento de acceso con un correo que no existe no
    # pertenece a ninguna empresa, y las acciones del panel de plataforma se anotan con la empresa afectada.
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True, nullable=True)

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
