from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import require_role
from app.db.session import get_db
from app.models.material import Material
from app.models.product import Product
from app.models.quote import Quote, QuoteHistory, QuoteItem
from app.schemas.quote import QuoteCreate, QuoteHistoryOut, QuoteOut, QuoteUpdate, RejectIn
from app.services.code_generator import next_code
from app.services.quote_archiver import archive_stale_quotes
from app.services.totals import LineInput, compute_totals

router = APIRouter(tags=["quotes"])

allowed_roles = require_role("admin", "oficina")


def _get_quote(db: Session, quote_id: int) -> Quote:
    quote = db.query(Quote).options(joinedload(Quote.items)).filter(Quote.id == quote_id).one_or_none()
    if quote is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return quote


def _resolve_item_fields(db: Session, product_id: int | None, description: str, unit_price: float) -> tuple[str, float]:
    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Producto {product_id} no encontrado")
        description = description or product.name
        if not unit_price:
            unit_price = float(product.price)
    return description, unit_price


def _build_quote_items(db: Session, quote: Quote, items_in) -> None:
    settings = get_settings()
    for item in items_in:
        description, unit_price = _resolve_item_fields(db, item.product_id, item.description, item.unit_price)
        quote.items.append(
            QuoteItem(
                product_id=item.product_id,
                description=description,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=round(item.quantity * unit_price, 2),
            )
        )
    lines = [LineInput(item.quantity, item.unit_price) for item in quote.items]
    quote.subtotal, quote.itbis, quote.total = compute_totals(lines, settings.itbis_rate)


@router.get("/api/projects/{project_id}/quotes", response_model=list[QuoteOut])
def list_project_quotes(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    archive_stale_quotes(db, project_id=project_id)
    return (
        db.query(Quote)
        .options(joinedload(Quote.items))
        .filter(Quote.project_id == project_id)
        .order_by(Quote.created_at.desc())
        .all()
    )


@router.get("/api/quotes", response_model=list[QuoteOut])
def list_quotes(status_filter: str | None = None, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    archive_stale_quotes(db)
    query = db.query(Quote).options(joinedload(Quote.items))
    if status_filter:
        query = query.filter(Quote.status == status_filter)
    return query.order_by(Quote.created_at.desc()).all()


@router.post("/api/projects/{project_id}/quotes", response_model=QuoteOut, status_code=status.HTTP_201_CREATED)
def create_quote(project_id: int, payload: QuoteCreate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    code = next_code(db, "COT")
    quote = Quote(code=code, project_id=project_id, notes=payload.notes)
    _build_quote_items(db, quote, payload.items)

    db.add(quote)
    db.flush()
    db.add(QuoteHistory(quote_id=quote.id, action="creada"))
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/api/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    archive_stale_quotes(db)
    return _get_quote(db, quote_id)


@router.put("/api/quotes/{quote_id}", response_model=QuoteOut)
def update_quote(quote_id: int, payload: QuoteUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    quote = _get_quote(db, quote_id)
    if quote.status != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden editar cotizaciones pendientes")

    quote.notes = payload.notes
    quote.items.clear()
    db.flush()
    _build_quote_items(db, quote, payload.items)
    db.add(QuoteHistory(quote_id=quote.id, action="editada"))
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/api/quotes/{quote_id}/approve", response_model=QuoteOut)
def approve_quote(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    quote = _get_quote(db, quote_id)
    if quote.status not in ("pendiente", "archivada"):
        raise HTTPException(status_code=400, detail=f"No se puede aprobar una cotización '{quote.status}'")
    quote.status = "aprobada"
    quote.decided_at = datetime.now(timezone.utc)
    db.add(QuoteHistory(quote_id=quote.id, action="aprobada"))

    # Genera la lista de materiales (§18) a partir de las líneas de la cotización aprobada,
    # una sola vez por cotización aunque se re-apruebe tras reactivar.
    already_generated = db.query(Material).filter(Material.source_quote_id == quote.id).first() is not None
    if not already_generated:
        for item in quote.items:
            db.add(
                Material(
                    project_id=quote.project_id,
                    product_id=item.product_id,
                    source_quote_id=quote.id,
                    description=item.description,
                    quantity=item.quantity,
                    status="pendiente_compra",
                )
            )

    db.commit()
    db.refresh(quote)
    return quote


@router.post("/api/quotes/{quote_id}/reject", response_model=QuoteOut)
def reject_quote(quote_id: int, payload: RejectIn, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    quote = _get_quote(db, quote_id)
    if quote.status not in ("pendiente", "archivada"):
        raise HTTPException(status_code=400, detail=f"No se puede rechazar una cotización '{quote.status}'")
    quote.status = "no_aprobada"
    quote.decided_at = datetime.now(timezone.utc)
    db.add(QuoteHistory(quote_id=quote.id, action="rechazada", note=payload.reason))
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/api/quotes/{quote_id}/archive", response_model=QuoteOut)
def archive_quote(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    quote = _get_quote(db, quote_id)
    quote.status = "archivada"
    db.add(QuoteHistory(quote_id=quote.id, action="archivada", note="Archivada manualmente"))
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/api/quotes/{quote_id}/reactivate", response_model=QuoteOut)
def reactivate_quote(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    quote = _get_quote(db, quote_id)
    if quote.status != "archivada":
        raise HTTPException(status_code=400, detail="Solo se pueden reactivar cotizaciones archivadas")
    quote.status = "pendiente"
    quote.decided_at = None
    db.add(QuoteHistory(quote_id=quote.id, action="reactivada"))
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/api/quotes/{quote_id}/history", response_model=list[QuoteHistoryOut])
def get_quote_history(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    _get_quote(db, quote_id)  # 404 si no existe
    return (
        db.query(QuoteHistory)
        .filter(QuoteHistory.quote_id == quote_id)
        .order_by(QuoteHistory.created_at)
        .all()
    )
