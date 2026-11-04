import logging
from datetime import datetime, timezone


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import require_role
from app.db.session import get_db
from app.models.material import Material
from app.models.product import Product
from app.models.quote import Quote, QuoteHistory, QuoteItem
from app.models.user import User
from app.schemas.margin import MarginSummary
from app.schemas.quote import (
    PriceChange,
    PurchaseListPreviewOut,
    QuoteCreate,
    QuoteHistoryOut,
    QuoteOut,
    QuotePdfPhotos,
    QuotePdfVariant,
    QuoteSendEmailIn,
    QuoteSendEmailOut,
    QuoteUpdate,
    RepriceOut,
    RepricePreviewOut,
    RejectIn,
)
from app.services import email as email_service
from app.services.audit import audit
from app.services.company import load_company
from app.services.code_generator import next_code
from app.services.margin import compute_margin
from app.services.notifications import notify_quote_pending
from app.services.pdf import build_quote_pdf
from app.services.photo_annex import collect_photos
from app.services.quote_approval import build_material_rows_from_quote, mark_quote_approved
from app.services.document_items import resolve_item_fields
from app.services.quote_archiver import archive_stale_quotes
from app.services.totals import LineInput, compute_totals

router = APIRouter(tags=["quotes"])
logger = logging.getLogger("multitec.quotes")

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


def _get_quote(db: Session, quote_id: int) -> Quote:
    quote = db.query(Quote).options(joinedload(Quote.items)).filter(Quote.id == quote_id).one_or_none()
    if quote is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return quote


def _build_quote_items(db: Session, quote: Quote, items_in) -> None:
    settings = get_settings()
    for item in items_in:
        description, unit_price = resolve_item_fields(db, item.product_id, item.description, item.unit_price)
        quote.items.append(
            QuoteItem(
                product_id=item.product_id,
                description=description,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=round(item.quantity * unit_price, 2),
                note=item.note,
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
def create_quote(
    project_id: int, payload: QuoteCreate, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)
):
    code = next_code(db, "COT")
    quote = Quote(code=code, project_id=project_id, notes=payload.notes, created_by=current_user.id)
    _build_quote_items(db, quote, payload.items)

    db.add(quote)
    db.flush()
    db.add(QuoteHistory(quote_id=quote.id, action="creada"))
    db.commit()
    db.refresh(quote)
    notify_quote_pending(db, quote)
    return quote


@router.get("/api/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    archive_stale_quotes(db)
    return _get_quote(db, quote_id)


_PDF_SUFFIX = {"detallada": "", "ejecutiva": "-ejecutiva", "global": "-monto-general"}


def _render_quote_pdf(db: Session, quote: Quote, variant: str, photos: str) -> tuple[bytes, str]:
    """PDF de la cotización en el formato pedido y su nombre de archivo (mismo para ver, descargar y enviar)."""
    category_by_product_id = {}
    if variant == "ejecutiva":
        product_ids = [item.product_id for item in quote.items if item.product_id is not None]
        if product_ids:
            products = db.query(Product).options(joinedload(Product.category)).filter(Product.id.in_(product_ids)).all()
            category_by_product_id = {p.id: p.category_name for p in products}

    annex = collect_photos(quote.project.survey, photos)
    pdf_bytes = build_quote_pdf(
        quote, variant=variant, category_by_product_id=category_by_product_id, photo_annex=annex
    )
    photo_suffix = "-fotos" if photos != "none" else ""
    return pdf_bytes, f"{quote.code}{_PDF_SUFFIX.get(variant, '')}{photo_suffix}.pdf"


@router.get("/api/quotes/{quote_id}/pdf")
def get_quote_pdf(
    quote_id: int,
    variant: QuotePdfVariant = "detallada",
    photos: QuotePdfPhotos = "none",
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    quote = _get_quote(db, quote_id)
    pdf_bytes, filename = _render_quote_pdf(db, quote, variant, photos)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


_VARIANT_LABELS = {"detallada": "detallada", "ejecutiva": "resumen por categoría", "global": "monto general"}


@router.post("/api/quotes/{quote_id}/send-email", response_model=QuoteSendEmailOut)
def send_quote_email(
    quote_id: int,
    payload: QuoteSendEmailIn,
    db: Session = Depends(get_db),
    user: User = Depends(allowed_roles),
):
    """Envía al cliente la cotización por correo con el PDF adjunto, en el formato elegido. A diferencia de los
    avisos automáticos, aquí el usuario pidió el envío: si el correo no está configurado o falla, se le dice."""
    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El envío por correo no está configurado en el servidor (falta SMTP). Usa WhatsApp o descarga el PDF.",
        )
    quote = _get_quote(db, quote_id)
    pdf_bytes, filename = _render_quote_pdf(db, quote, payload.variant, payload.photos)
    client = quote.project.client
    company_name = load_company(quote.company_id).name or "Multitec"
    subject = f"Cotización {quote.code} — {company_name}"
    greeting = f"Hola {client.name}," if client.name else "Hola,"
    body = (payload.message or "").strip() or (
        f"{greeting}\n\nLe compartimos la cotización {quote.code} por un total de "
        f"RD$ {float(quote.total):,.2f}. Adjuntamos el PDF.\n\nQuedamos atentos a cualquier pregunta.\n\n{company_name}"
    )
    try:
        email_service.deliver_email(str(payload.to), subject, body, attachment=(filename, pdf_bytes, "application/pdf"))
    except Exception:
        logger.exception("No se pudo enviar la cotización %s a %s", quote.code, payload.to)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El servidor de correo no aceptó el envío. Intenta de nuevo o envíala por WhatsApp.",
        )
    db.add(
        QuoteHistory(
            quote_id=quote.id,
            action="enviada",
            note=f"Por correo a {payload.to} ({_VARIANT_LABELS[payload.variant]})",
        )
    )
    audit(db, "cotizacion.enviada", user=user, entity="quote", entity_id=quote.id,
          detail={"canal": "correo", "a": str(payload.to), "formato": payload.variant})
    db.commit()
    return QuoteSendEmailOut(sent_to=str(payload.to), filename=filename)


@router.get("/api/quotes/{quote_id}/margin", response_model=MarginSummary)
def get_quote_margin(quote_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    quote = _get_quote(db, quote_id)
    return compute_margin(db, quote.items, basis="cotizado")


@router.get("/api/quotes/{quote_id}/purchase-list-preview", response_model=PurchaseListPreviewOut)
def get_purchase_list_preview(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    """§ Motor 6 — lista de compras preliminar: lo que se generaría como `Material` si
    esta cotización se aprobara ahora, sin crear nada todavía (ver
    `build_material_rows_from_quote`, compartida con la aprobación real para que ambas
    nunca puedan divergir)."""
    quote = _get_quote(db, quote_id)
    already_generated = db.query(Material).filter(Material.source_quote_id == quote.id).first() is not None
    return PurchaseListPreviewOut(
        quote_id=quote.id,
        already_generated=already_generated,
        items=build_material_rows_from_quote(quote),
    )


@router.put("/api/quotes/{quote_id}", response_model=QuoteOut)
def update_quote(quote_id: int, payload: QuoteUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    quote = _get_quote(db, quote_id)
    if quote.status != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden editar cotizaciones pendientes")

    quote.notes = payload.notes
    quote.items.clear()
    quote.stale_notified = False
    db.flush()
    _build_quote_items(db, quote, payload.items)
    db.add(QuoteHistory(quote_id=quote.id, action="editada"))
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/api/quotes/{quote_id}/approve", response_model=QuoteOut)
def approve_quote(quote_id: int, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    # Bloquea la fila hasta el commit — mismo motivo que en public.py::approve_public_quote:
    # dos aprobaciones concurrentes no deben generar Material/prefactura duplicados.
    quote = db.get(Quote, quote_id, with_for_update=True)
    if quote is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if quote.status not in ("pendiente", "archivada"):
        raise HTTPException(status_code=400, detail=f"No se puede aprobar una cotización '{quote.status}'")
    mark_quote_approved(db, quote, created_by=current_user.id)
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
    if quote.status != "pendiente":
        raise HTTPException(status_code=400, detail=f"No se puede archivar una cotización '{quote.status}'")
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


# --- Actualizar precios y nuevas versiones --------------------------------------------------------------------------


def _price_changes(db: Session, quote: Quote) -> list[tuple[QuoteItem, float]]:
    """Líneas cuyo precio ya no coincide con el del catálogo. Las líneas sin producto (texto libre) no se tocan."""
    ids = {item.product_id for item in quote.items if item.product_id is not None}
    prices = {p.id: float(p.price) for p in db.query(Product).filter(Product.id.in_(ids)).all()} if ids else {}
    out = []
    for item in quote.items:
        new = prices.get(item.product_id) if item.product_id is not None else None
        if new is not None and new > 0 and abs(new - float(item.unit_price)) > 0.005:
            out.append((item, new))
    return out


def _totals_with(quote: Quote, overrides: dict[int, float]) -> float:
    settings = get_settings()
    lines = [LineInput(i.quantity, overrides.get(i.id, float(i.unit_price))) for i in quote.items]
    return float(compute_totals(lines, settings.itbis_rate)[2])


def _change_rows(changes: list[tuple[QuoteItem, float]]) -> list[PriceChange]:
    return [
        PriceChange(
            item_id=item.id,
            description=item.description,
            quantity=float(item.quantity),
            old_price=float(item.unit_price),
            new_price=new,
        )
        for item, new in changes
    ]


def _copy_as_new_version(db: Session, quote: Quote, user: User, prices: dict[int, float]) -> Quote:
    """Cotización nueva (pendiente) con las mismas líneas y, si se piden, otros precios: para corregir algo que ya no
    se puede editar (aprobada, rechazada) sin tocar lo que el cliente ya vio."""
    settings = get_settings()
    new = Quote(
        code=next_code(db, "COT"),
        project_id=quote.project_id,
        source_budget_id=quote.source_budget_id,
        notes=quote.notes,
        created_by=user.id,
    )
    for item in quote.items:
        price = prices.get(item.id, float(item.unit_price))
        new.items.append(
            QuoteItem(
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=price,
                subtotal=round(float(item.quantity) * price, 2),
                note=item.note,
            )
        )
    lines = [LineInput(i.quantity, i.unit_price) for i in new.items]
    new.subtotal, new.itbis, new.total = compute_totals(lines, settings.itbis_rate)
    db.add(new)
    db.flush()
    db.add(QuoteHistory(quote_id=new.id, action="creada", note=f"Nueva versión de {quote.code}"))
    db.add(QuoteHistory(quote_id=quote.id, action="nueva_version", note=f"Se creó {new.code}"))
    return new


@router.get("/api/quotes/{quote_id}/reprice-preview", response_model=RepricePreviewOut)
def reprice_preview(quote_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    quote = _get_quote(db, quote_id)
    changes = _price_changes(db, quote)
    return RepricePreviewOut(
        changes=_change_rows(changes),
        total_old=float(quote.total),
        total_new=_totals_with(quote, {item.id: new for item, new in changes}),
    )


@router.post("/api/quotes/{quote_id}/reprice", response_model=RepriceOut)
def reprice_quote(quote_id: int, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    """Vuelve a poner los precios actuales del catálogo. Una cotización pendiente se actualiza en su lugar; si ya no se
    puede editar (aprobada, rechazada, archivada) se crea una nueva versión pendiente y la original queda intacta."""
    quote = _get_quote(db, quote_id)
    changes = _price_changes(db, quote)
    if not changes:
        raise HTTPException(status_code=400, detail="Los precios de esta cotización ya son los del catálogo")
    rows = _change_rows(changes)
    new_prices = {item.id: new for item, new in changes}

    if quote.status == "pendiente":
        settings = get_settings()
        for item, new in changes:
            item.unit_price = new
            item.subtotal = round(float(item.quantity) * new, 2)
        lines = [LineInput(i.quantity, i.unit_price) for i in quote.items]
        quote.subtotal, quote.itbis, quote.total = compute_totals(lines, settings.itbis_rate)
        quote.stale_notified = False
        db.add(QuoteHistory(quote_id=quote.id, action="repreciada", note=f"{len(changes)} precio(s) actualizado(s)"))
        result, created_new = quote, False
    else:
        result, created_new = _copy_as_new_version(db, quote, current_user, new_prices), True
        db.add(QuoteHistory(quote_id=result.id, action="repreciada", note=f"{len(changes)} precio(s) actualizado(s)"))
    db.commit()
    db.refresh(result)
    return RepriceOut(quote=result, created_new=created_new, changes=rows)


@router.post("/api/quotes/{quote_id}/new-version", response_model=QuoteOut, status_code=status.HTTP_201_CREATED)
def new_quote_version(quote_id: int, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    """Copia la cotización como una nueva pendiente para poder editarla (con la original aprobada o rechazada no se puede)."""
    quote = _get_quote(db, quote_id)
    new = _copy_as_new_version(db, quote, current_user, {})
    db.commit()
    db.refresh(new)
    return new
