from sqlalchemy.orm import Session

from app.models.sequence import CodeSequence


def next_code(db: Session, prefix: str, padding: int = 6) -> str:
    """Devuelve el próximo código correlativo para un prefijo (PRY, CAM, NVR...).

    Usa SELECT ... FOR UPDATE dentro de la transacción activa para evitar
    duplicados si dos requests generan un código al mismo tiempo (no-op en
    SQLite, pero efectivo en PostgreSQL).
    """
    sequence = db.query(CodeSequence).filter(CodeSequence.prefix == prefix).with_for_update().one_or_none()
    if sequence is None:
        sequence = CodeSequence(prefix=prefix, last_value=0)
        db.add(sequence)
        db.flush()

    sequence.last_value += 1
    db.flush()
    return f"{prefix}-{sequence.last_value:0{padding}d}"
