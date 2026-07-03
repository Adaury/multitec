import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.limiter import limiter
from app.core.security import require_role
from app.db.session import get_db
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote
from app.schemas.public import PublicLinkOut, PublicProjectOut
from app.services.pdf import build_invoice_pdf

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
        )
        .filter(Project.public_token == token)
        .one_or_none()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Enlace no válido")
    return project


@router.get("/api/public/projects/{token}", response_model=PublicProjectOut)
@limiter.limit("30/minute")
def get_public_project(request: Request, token: str, db: Session = Depends(get_db)):
    project = _get_project_by_token(db, token)
    return {
        "code": project.code,
        "status": project.status,
        "date": project.date,
        "description": project.description,
        "client_name": project.client.name,
        "quotes": project.quotes,
        "invoices": project.invoices,
    }


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
