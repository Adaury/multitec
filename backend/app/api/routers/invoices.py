from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.invoice import Invoice, InvoiceHistory, InvoiceItem, PreInvoice, PreInvoiceItem
from app.models.product import Product
from app.models.quote import Quote
from app.models.user import User
from app.schemas.invoice import InvoiceHistoryOut, InvoiceOut, PreInvoiceCreate, PreInvoiceOut
from app.services.code_generator import next_code
from app.services.totals import LineInput, compute_totals

router = APIRouter(tags=["invoices"])

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


def _resolve_item_fields(db: Session, product_id: int | None, description: str, unit_price: float) -> tuple[str, float]:
    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Producto {product_id} no encontrado")
        description = description or product.name
        if not unit_price:
            unit_price = float(product.price)
    return description, unit_price


def _get_pre_invoice(db: Session, pre_invoice_id: int) -> PreInvoice:
    pre_invoice = (
        db.query(PreInvoice)
        .options(joinedload(PreInvoice.items))
        .filter(PreInvoice.id == pre_invoice_id)
        .one_or_none()
    )
    if pre_invoice is None:
        raise HTTPException(status_code=404, detail="Prefactura no encontrada")
    return pre_invoice


@router.get("/api/projects/{project_id}/pre-invoices", response_model=list[PreInvoiceOut])
def list_pre_invoices(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(PreInvoice)
        .options(joinedload(PreInvoice.items))
        .filter(PreInvoice.project_id == project_id)
        .order_by(PreInvoice.created_at.desc())
        .all()
    )


@router.post("/api/projects/{project_id}/pre-invoices", response_model=PreInvoiceOut, status_code=status.HTTP_201_CREATED)
def create_pre_invoice(
    project_id: int,
    payload: PreInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    code = next_code(db, "PFC")
    pre_invoice = PreInvoice(code=code, project_id=project_id, notes=payload.notes, created_by=current_user.id)

    for item in payload.items:
        description, unit_price = _resolve_item_fields(db, item.product_id, item.description, item.unit_price)
        pre_invoice.items.append(
            PreInvoiceItem(
                product_id=item.product_id,
                description=description,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=round(item.quantity * unit_price, 2),
            )
        )

    lines = [LineInput(item.quantity, item.unit_price) for item in pre_invoice.items]
    pre_invoice.subtotal, pre_invoice.itbis, pre_invoice.total = compute_totals(lines, 0.18)

    db.add(pre_invoice)
    db.commit()
    db.refresh(pre_invoice)
    return pre_invoice


@router.post("/api/quotes/{quote_id}/generate-pre-invoice", response_model=PreInvoiceOut, status_code=status.HTTP_201_CREATED)
def generate_pre_invoice(quote_id: int, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    quote = db.query(Quote).options(joinedload(Quote.items)).filter(Quote.id == quote_id).one_or_none()
    if quote is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if quote.status != "aprobada":
        raise HTTPException(status_code=400, detail="Solo se puede generar prefactura de una cotización aprobada")

    code = next_code(db, "PFC")
    pre_invoice = PreInvoice(
        code=code,
        project_id=quote.project_id,
        source_quote_id=quote.id,
        notes=quote.notes,
        subtotal=quote.subtotal,
        itbis=quote.itbis,
        total=quote.total,
        created_by=current_user.id,
    )
    for item in quote.items:
        pre_invoice.items.append(
            PreInvoiceItem(
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
        )

    db.add(pre_invoice)
    db.commit()
    db.refresh(pre_invoice)
    return pre_invoice


@router.get("/api/pre-invoices/{pre_invoice_id}", response_model=PreInvoiceOut)
def get_pre_invoice(pre_invoice_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return _get_pre_invoice(db, pre_invoice_id)


@router.post("/api/pre-invoices/{pre_invoice_id}/convert-to-invoice", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def convert_to_invoice(pre_invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    """§13-14: 'el administrador decide convertir a factura' — único endpoint admin-only."""
    pre_invoice = _get_pre_invoice(db, pre_invoice_id)
    if pre_invoice.status == "facturada":
        raise HTTPException(status_code=400, detail="Esta prefactura ya fue facturada")

    code = next_code(db, "FAC")
    invoice = Invoice(
        code=code,
        project_id=pre_invoice.project_id,
        pre_invoice_id=pre_invoice.id,
        subtotal=pre_invoice.subtotal,
        itbis=pre_invoice.itbis,
        total=pre_invoice.total,
        created_by=current_user.id,
    )
    for item in pre_invoice.items:
        invoice.items.append(
            InvoiceItem(
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
        )

    pre_invoice.status = "facturada"
    db.add(invoice)
    db.flush()
    db.add(InvoiceHistory(invoice_id=invoice.id, action="creada", note=f"Convertida desde prefactura {pre_invoice.code}"))
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/api/projects/{project_id}/invoices", response_model=list[InvoiceOut])
def list_invoices(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(Invoice)
        .options(joinedload(Invoice.items))
        .filter(Invoice.project_id == project_id)
        .order_by(Invoice.created_at.desc())
        .all()
    )


@router.get("/api/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    invoice = db.query(Invoice).options(joinedload(Invoice.items)).filter(Invoice.id == invoice_id).one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


@router.get("/api/invoices/{invoice_id}/history", response_model=list[InvoiceHistoryOut])
def get_invoice_history(invoice_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return (
        db.query(InvoiceHistory)
        .filter(InvoiceHistory.invoice_id == invoice_id)
        .order_by(InvoiceHistory.created_at)
        .all()
    )
