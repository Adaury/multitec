from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LogEntry(Base):
    """Bitácora (§12) — registro cronológico del proyecto."""

    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    comment: Mapped[str] = mapped_column(Text)
    entry_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="log_entries")
    responsible: Mapped["User"] = relationship()
    assets: Mapped[list["LogEntryAsset"]] = relationship(back_populates="entry", cascade="all, delete-orphan")


class LogEntryAsset(Base):
    __tablename__ = "log_entry_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_entry_id: Mapped[int] = mapped_column(ForeignKey("log_entries.id"))
    file_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entry: Mapped["LogEntry"] = relationship(back_populates="assets")
