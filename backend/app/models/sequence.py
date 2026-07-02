from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CodeSequence(Base):
    """Tracks the last used correlative number per code prefix (PRY, CAM, NVR, CAB, SW...)."""

    __tablename__ = "code_sequences"

    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
