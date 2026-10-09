from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.project import Project
from app.models.purchase_invoice import PurchaseInvoice
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.purchase_invoice import PurchaseInvoiceCreate, PurchaseInvoiceOut, PurchaseInvoiceUpdate

router = APIRouter(prefix="/api/purchase-invoices", tags=["purchase-invoices"])

# Igual que proveedores/materiales: compras no es del rol tecnico.
allowed_roles = require_role("admin", "oficina")


def _out(invoice: PurchaseInvoice) -> PurchaseInvoiceOut:
    out = PurchaseInvoiceOut.model_validate(invoice)
    out.supplier_name = invoice.supplier.name if invoice.supplier else None
    return out


def _validate_refs(db: Session, payload: PurchaseInvoiceCreate) -> None:
    if db.get(Supplier, payload.supplier_id) is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if payload.project_id is not None and db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")


def _check_duplicate(db: Session, payload: PurchaseInvoiceCreate, exclude_id: int | None = None) -> None:
    query = db.query(PurchaseInvoice).filter(
        PurchaseInvoice.supplier_id == payload.supplier_id, PurchaseInvoice.ncf == payload.ncf
    )
    if exclude_id is not None:
        query = query.filter(PurchaseInvoice.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=409, detail="Ya existe una factura de este proveedor con ese NCF")


@router.get("", response_model=list[PurchaseInvoiceOut])
def list_purchase_invoices(
    supplier_id: int | None = None, db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    query = db.query(PurchaseInvoice).options(joinedload(PurchaseInvoice.supplier))
    if supplier_id is not None:
        query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
    invoices = query.order_by(PurchaseInvoice.invoice_date.desc(), PurchaseInvoice.id.desc()).all()
    return [_out(i) for i in invoices]


@router.post("", response_model=PurchaseInvoiceOut, status_code=status.HTTP_201_CREATED)
def create_purchase_invoice(
    payload: PurchaseInvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)
):
    _validate_refs(db, payload)
    _check_duplicate(db, payload)
    invoice = PurchaseInvoice(**payload.model_dump(), created_by=current_user.id)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return _out(invoice)


@router.get("/{invoice_id}", response_model=PurchaseInvoiceOut)
def get_purchase_invoice(invoice_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    invoice = db.get(PurchaseInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura de compra no encontrada")
    return _out(invoice)


@router.put("/{invoice_id}", response_model=PurchaseInvoiceOut)
def update_purchase_invoice(
    invoice_id: int, payload: PurchaseInvoiceUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    invoice = db.get(PurchaseInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura de compra no encontrada")
    _validate_refs(db, payload)
    _check_duplicate(db, payload, exclude_id=invoice_id)
    for field, value in payload.model_dump().items():
        setattr(invoice, field, value)
    db.commit()
    db.refresh(invoice)
    return _out(invoice)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_invoice(invoice_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    invoice = db.get(PurchaseInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura de compra no encontrada")
    db.delete(invoice)
    db.commit()
