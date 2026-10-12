import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.limiter import limiter
from app.core.security import require_role
from app.db.session import get_db
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote, QuoteHistory
from app.models.ticket import Ticket
from app.schemas.public import PublicApproveIn, PublicLinkOut, PublicProjectOut, PublicRejectIn
from app.services.notifications import (
    notify_portal_first_viewed,
    notify_quote_approved_by_client,
    notify_quote_rejected_by_client,
)
from app.services.pdf import build_invoice_pdf, build_quote_pdf
from app.services.photo_annex import collect_photos
from app.services.quote_approval import mark_quote_approved

router = APIRouter(tags=["public"])

manage_roles = require_role("admin", "oficina")


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.post("/api/projects/{project_id}/public-link", response_model=PublicLinkOut)
def create_or_rotate_public_link(project_id: int, db: Session = Depends(get_db), _=Depends(manage_roles)):
    """Genera (o regenera, invalidando el anterior) el enlace del portal de cliente."""
    project = _get_project_or_404(db, project_id)
    project.public_token = secrets.token_urlsafe(32)
    db.commit()
    return {"token": project.public_token}


@router.delete("/api/projects/{project_id}/public-link", status_code=status.HTTP_204_NO_CONTENT)
def revoke_public_link(project_id: int, db: Session = Depends(get_db), _=Depends(manage_roles)):
    project = _get_project_or_404(db, project_id)
    project.public_token = None
    db.commit()


def _get_project_by_token(db: Session, token: str) -> Project:
    project = (
        db.query(Project)
        .options(
            joinedload(Project.client),
            joinedload(Project.quotes).joinedload(Quote.items),
            joinedload(Project.invoices).joinedload(Invoice.items),
            joinedload(Project.tickets).joinedload(Ticket.technician),
            joinedload(Project.survey),
        )
        .filter(Project.public_token == token)
        .one_or_none()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    return project


def _serialize_public_project(project: Project) -> dict:
    return {
        "code": project.code,
        "status": project.status,
        "date": project.date,
        "description": project.description,
        "client_name": project.client.name,
        "quotes": project.quotes,
        "invoices": [inv for inv in project.invoices if inv.voided_at is None],
        "tickets": [
            {
                "code": ticket.code,
                "problem": ticket.problem,
                "solution": ticket.solution,
                "status": ticket.status,
                "technician_name": ticket.technician.name if ticket.technician else None,
                "created_at": ticket.created_at,
                "resolved_at": ticket.resolved_at,
            }
            for ticket in project.tickets
        ],
    }


@router.get("/api/public/projects/{token}", response_model=PublicProjectOut)
@limiter.limit("30/minute")
def get_public_project(request: Request, token: str, db: Session = Depends(get_db)):
    project = _get_project_by_token(db, token)
    is_first_view = project.portal_first_viewed_at is None
    now = datetime.now(timezone.utc)
    if is_first_view:
        project.portal_first_viewed_at = now
    project.portal_last_viewed_at = now
    db.commit()
    if is_first_view:
        notify_portal_first_viewed(db, project)
    return _serialize_public_project(project)


@router.post("/api/public/projects/{token}/quotes/{quote_id}/approve", response_model=PublicProjectOut)
@limiter.limit("30/minute")
def approve_public_quote(
    request: Request,
    token: str,
    quote_id: int,
    payload: PublicApproveIn | None = None,
    db: Session = Depends(get_db),
):
    project = _get_project_by_token(db, token)
    if not any(q.id == quote_id for q in project.quotes):
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    # Bloquea la fila hasta el commit: dos aprobaciones concurrentes del mismo quote_id
    # (doble clic, reintento de red) no deben generar Material/prefactura duplicados —
    # sin esto, ambas requests leerían status='pendiente' antes de que cualquiera confirme.
    quote = db.get(Quote, quote_id, with_for_update=True)
    if quote.status != "pendiente":
        raise HTTPException(status_code=400, detail=f"No se puede aprobar una cotización '{quote.status}'")
    signer = (payload.signer_name or "").strip() if payload else ""
    note = "Aprobada por el cliente desde el portal" + (f" — firmó: {signer}" if signer else "")
    mark_quote_approved(db, quote, created_by=None, note=note)
    db.commit()
    notify_quote_approved_by_client(db, quote)
    project = _get_project_by_token(db, token)
    return _serialize_public_project(project)


@router.post("/api/public/projects/{token}/quotes/{quote_id}/reject", response_model=PublicProjectOut)
@limiter.limit("30/minute")
def reject_public_quote(
    request: Request,
    token: str,
    quote_id: int,
    payload: PublicRejectIn | None = None,
    db: Session = Depends(get_db),
):
    """El cliente rechaza la cotización desde su enlace (con motivo opcional). Queda 'no
    aprobada' igual que si la hubiera rechazado la oficina, y se avisa a los admins."""
    project = _get_project_by_token(db, token)
    if not any(q.id == quote_id for q in project.quotes):
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    quote = db.get(Quote, quote_id, with_for_update=True)
    if quote.status != "pendiente":
        raise HTTPException(status_code=400, detail=f"No se puede rechazar una cotización '{quote.status}'")
    reason = (payload.reason or "").strip() if payload else ""
    signer = (payload.signer_name or "").strip() if payload else ""
    note = "Rechazada por el cliente desde el portal"
    if signer:
        note += f" — {signer}"
    if reason:
        note += f": {reason}"
    quote.status = "no_aprobada"
    quote.decided_at = datetime.now(timezone.utc)
    db.add(QuoteHistory(quote_id=quote.id, action="rechazada", note=note))
    db.commit()
    notify_quote_rejected_by_client(db, quote, reason)
    project = _get_project_by_token(db, token)
    return _serialize_public_project(project)


@router.get("/api/public/projects/{token}/quotes/{quote_id}/pdf")
@limiter.limit("30/minute")
def get_public_quote_pdf(request: Request, token: str, quote_id: int, db: Session = Depends(get_db)):
    """PDF de la cotización con el anexo de fotos marcadas (si el levantamiento las tiene)."""
    project = _get_project_by_token(db, token)
    quote = next((q for q in project.quotes if q.id == quote_id), None)
    if quote is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    annex = collect_photos(project.survey, "marked")
    pdf_bytes = build_quote_pdf(quote, photo_annex=annex)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.code}.pdf"'},
    )


@router.get("/api/public/projects/{token}/invoices/{invoice_id}/pdf")
@limiter.limit("30/minute")
def get_public_invoice_pdf(request: Request, token: str, invoice_id: int, db: Session = Depends(get_db)):
    project = _get_project_by_token(db, token)
    invoice = next((inv for inv in project.invoices if inv.id == invoice_id), None)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    pdf_bytes = build_invoice_pdf(invoice)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.code}.pdf"'},
    )
