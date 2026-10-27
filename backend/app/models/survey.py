from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.tenant import TenantMixin


class Survey(TenantMixin, Base):
    """Levantamiento técnico — 1:1 con Project."""

    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurements: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # gancho para IA (Fase 5)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="survey")
    assets: Mapped[list["SurveyAsset"]] = relationship(back_populates="survey", cascade="all, delete-orphan")


class SurveyAsset(TenantMixin, Base):
    """Foto o audio adjunto a un levantamiento."""

    __tablename__ = "survey_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # photo | audio
    file_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["Survey"] = relationship(back_populates="assets")
    markers: Mapped[list["SurveyMarker"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", order_by="SurveyMarker.number"
    )


class SurveyMarker(TenantMixin, Base):
    """Punto numerado sobre una foto (cámara 1, NVR, switch...). `x`/`y` van de 0 a 1 sobre el
    ancho y alto de la imagen, así que no dependen de cómo se muestre. La numeración es corrida
    en todo el levantamiento y la reasigna el backend."""

    __tablename__ = "survey_markers"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("survey_assets.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Tipo de equipo (camara, grabador, switch...): lo elige el técnico; si falta se deduce del nombre (services/survey_points.py).
    kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped["SurveyAsset"] = relationship(back_populates="markers")

    @property
    def point_kind(self) -> str:
        from app.services.survey_points import marker_kind  # import tardío: el servicio importa este modelo

        return marker_kind(self)
