from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Los tres action_type con manejador implementado (ver app/ai_engine/rules.py). Agregar
# uno nuevo no requiere migración — sus parámetros propios van en `action_params` (JSON),
# no en columnas — solo hace falta registrar el manejador nuevo ahí.
ACTION_TYPE_ADD_ACCESSORY = "add_accessory"
ACTION_TYPE_SET_CALCULATION_PARAMETER = "set_calculation_parameter"
ACTION_TYPE_FLAG_ENGINEERING_NOTE = "flag_engineering_note"
SUPPORTED_ACTION_TYPES = (
    ACTION_TYPE_ADD_ACCESSORY,
    ACTION_TYPE_SET_CALCULATION_PARAMETER,
    ACTION_TYPE_FLAG_ENGINEERING_NOTE,
)


class TechnicalRule(Base):
    """Regla técnica general (§ docs/ai-engine-architecture.md, Motor 4) — generalización
    hacia adelante de `CatalogRule`, que se mantiene intacta y sigue funcionando igual
    (tabla `catalog_rules`, sin migrar). Misma condición ("producto fuente presente en el
    presupuesto"); la acción es tipada y extensible en vez de estar fija a "agregar
    accesorio por cantidad".
    """

    __tablename__ = "technical_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    action_type: Mapped[str] = mapped_column(String(40))
    action_params: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_product: Mapped["Product"] = relationship(back_populates="technical_rules")  # noqa: F821

    # Accesores planos por action_type — permiten que TechnicalRuleOut
    # (schemas/technical_rule.py) se sirva con `from_attributes=True` igual que
    # CatalogRuleOut, sin que el frontend tenga que interpretar action_params a mano.
    @property
    def target_tag(self) -> str | None:
        return self.action_params.get("target_tag") if self.action_type == ACTION_TYPE_ADD_ACCESSORY else None

    @property
    def per_source_units(self) -> float | None:
        return self.action_params.get("per_source_units") if self.action_type == ACTION_TYPE_ADD_ACCESSORY else None

    @property
    def quantity(self) -> float:
        return self.action_params.get("quantity", 1) if self.action_type == ACTION_TYPE_ADD_ACCESSORY else 1

    @property
    def parameter_key(self) -> str | None:
        if self.action_type != ACTION_TYPE_SET_CALCULATION_PARAMETER:
            return None
        return self.action_params.get("parameter_key")

    @property
    def value(self) -> float | None:
        if self.action_type != ACTION_TYPE_SET_CALCULATION_PARAMETER:
            return None
        return self.action_params.get("value")

    @property
    def engineering_note(self) -> str | None:
        if self.action_type != ACTION_TYPE_FLAG_ENGINEERING_NOTE:
            return None
        return self.action_params.get("engineering_note")
