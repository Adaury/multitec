"""Subir una cotización ajena (competidor o proveedor) y compararla con el levantamiento y con la cotización propia.

Va solo para oficina y admin: son precios. El técnico no ve dinero (README → Roles y permisos)."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.quota import ai_quota
from app.core.security import require_role
from app.db.session import get_db
from app.models.project import Project
from app.models.quote import Quote
from app.models.quote_comparison import QuoteComparison
from app.models.user import User
from app.schemas.quote_comparison import ComparisonOut, ComparisonSummary, ComparisonUpdate
from app.services.audit import audit
from app.services.quote_compare import clean_items, compare, extract_text, read_items
from app.services.uploads import company_dir, enforce_matches_declared_type, read_upload, stored_extension

router = APIRouter(prefix="/api/projects/{project_id}/comparisons", tags=["comparisons"])

allowed_roles = require_role("admin", "oficina")
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def _project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


def _comparison(db: Session, project_id: int, comparison_id: int) -> QuoteComparison:
    row = (
        db.query(QuoteComparison)
        .filter(QuoteComparison.id == comparison_id, QuoteComparison.project_id == project_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")
    return row


def _our_quote(db: Session, project_id: int, quote_id: int | None) -> Quote | None:
    """La cotización indicada o, si no hay, la más reciente del proyecto que no esté rechazada."""
    query = db.query(Quote).filter(Quote.project_id == project_id)
    if quote_id is not None:
        return query.filter(Quote.id == quote_id).one_or_none()
    return query.filter(Quote.status != "no_aprobada").order_by(Quote.created_at.desc(), Quote.id.desc()).first()


def _out(db: Session, row: QuoteComparison) -> ComparisonOut:
    quote = _our_quote(db, row.project_id, row.quote_id)
    total = float(row.total) if row.total is not None else None
    result = compare(db, row.project_id, list(row.items or []), total, quote)
    return ComparisonOut(
        id=row.id,
        project_id=row.project_id,
        label=row.label,
        filename=row.filename,
        file_path=row.file_path,
        quote_id=row.quote_id,
        created_at=row.created_at,
        items=list(row.items or []),
        total=total,
        matched=result.matched,
        only_external=result.only_external,
        only_ours=result.only_ours,
        coverage=result.coverage,
        totals=result.totals,
    )


@router.get("", response_model=list[ComparisonSummary])
def list_comparisons(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    _project(db, project_id)
    rows = (
        db.query(QuoteComparison).filter(QuoteComparison.project_id == project_id).order_by(QuoteComparison.id.desc()).all()
    )
    return [
        ComparisonSummary(
            id=r.id,
            label=r.label,
            filename=r.filename,
            quote_id=r.quote_id,
            created_at=r.created_at,
            lines=len(r.items or []),
        )
        for r in rows
    ]


@router.post("", response_model=ComparisonOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(ai_quota)])
async def upload_comparison(
    project_id: int,
    label: str = Form(..., min_length=1, max_length=120),
    quote_id: int | None = Form(None),
    text: str | None = Form(None, max_length=20000),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    """Sube una cotización ajena (PDF con texto o foto) —o pega su texto— y la IA saca sus líneas. Esas líneas se pueden
    corregir antes de fiarse de la comparación."""
    _project(db, project_id)
    if quote_id is not None and _our_quote(db, project_id, quote_id) is None:
        raise HTTPException(status_code=404, detail="Cotización propia no encontrada en este proyecto")
    if file is None and not (text or "").strip():
        raise HTTPException(status_code=400, detail="Sube un PDF o una foto, o pega el texto de la cotización")

    file_path = filename = None
    if file is not None:
        base_type = (file.content_type or "").split(";")[0].strip().lower()
        if base_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="Sube un PDF o una foto (JPG, PNG o WebP)")
        contents = await read_upload(file)
        enforce_matches_declared_type(contents, file.content_type)
        source = extract_text(contents, base_type)  # puede fallar con un mensaje claro: antes de guardar nada
        folder = company_dir(db, "comparisons", str(project_id))
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"{uuid.uuid4().hex}{stored_extension(file.content_type)}"
        destination.write_bytes(contents)
        file_path, filename = str(destination.as_posix()), (file.filename or "")[:255] or None
    else:
        source = (text or "").strip()

    extracted = read_items(source)
    if not extracted.items:
        raise HTTPException(
            status_code=400,
            detail="No encontré líneas de productos en ese documento. Prueba con otro archivo o pega el texto.",
        )
    row = QuoteComparison(
        project_id=project_id,
        quote_id=quote_id,
        label=label.strip(),
        filename=filename,
        file_path=file_path,
        source_text=source,
        items=extracted.items,
        total=extracted.total,
        created_by=current_user.id,
    )
    db.add(row)
    db.flush()
    audit(db, "comparison_created", user=current_user, entity="project", entity_id=project_id, detail={"etiqueta": row.label})
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.get("/{comparison_id}", response_model=ComparisonOut)
def get_comparison(project_id: int, comparison_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return _out(db, _comparison(db, project_id, comparison_id))


@router.put("/{comparison_id}", response_model=ComparisonOut)
def update_comparison(
    project_id: int,
    comparison_id: int,
    payload: ComparisonUpdate,
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    row = _comparison(db, project_id, comparison_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("label"):
        row.label = data["label"].strip()
    if "quote_id" in data:
        if data["quote_id"] is not None and _our_quote(db, project_id, data["quote_id"]) is None:
            raise HTTPException(status_code=404, detail="Cotización propia no encontrada en este proyecto")
        row.quote_id = data["quote_id"]
    if payload.items is not None:
        row.items = clean_items([i.model_dump() for i in payload.items])
    if "total" in data:
        row.total = data["total"]
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.delete("/{comparison_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comparison(project_id: int, comparison_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    row = _comparison(db, project_id, comparison_id)
    db.delete(row)
    db.commit()
