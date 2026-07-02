from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.quote import Quote, QuoteHistory


def _as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def archive_stale_quotes(db: Session, project_id: int | None = None) -> int:
    """Marca como 'archivada' las cotizaciones 'pendiente' con más de N días sin decisión.

    Se ejecuta de forma perezosa (lazy) cada vez que se listan/consultan cotizaciones,
    para no requerir un scheduler en Fase 2. Devuelve la cantidad archivada.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=settings.quote_stale_days)

    query = db.query(Quote).filter(Quote.status == "pendiente")
    if project_id is not None:
        query = query.filter(Quote.project_id == project_id)

    archived_count = 0
    for quote in query.all():
        if _as_naive_utc(quote.created_at) <= cutoff:
            quote.status = "archivada"
            db.add(
                QuoteHistory(
                    quote_id=quote.id,
                    action="archivada",
                    note=f"Auto-archivada tras {settings.quote_stale_days} días sin aprobación.",
                )
            )
            archived_count += 1

    if archived_count:
        db.commit()
    return archived_count
