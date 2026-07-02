from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectEmbedding(Base):
    """Vector de embedding del expediente de un proyecto, usado para búsqueda semántica
    entre proyectos en '/api/ai/ask'. Se guarda como JSON (no ARRAY) para funcionar igual
    en SQLite y PostgreSQL sin depender de una extensión como pgvector."""

    __tablename__ = "project_embeddings"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    embedding: Mapped[list[float]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
