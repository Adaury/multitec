"""Panel de la plataforma: el dueño del sistema da de alta empresas, cada una con su administrador, y las suspende o
reactiva. Solo `is_platform_admin`. Todo se audita. Actúa sobre TODAS las empresas, por eso el filtro por empresa está
apagado en estas rutas (ver require_platform_admin) y cada escritura lleva su `company_id` explícito."""

import re
import secrets
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, require_platform_admin, revoke_all_refresh_tokens
from app.db.seed import seed_new_company
from app.db.session import SessionLocal, get_db
from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.user import User
from app.schemas.platform import (
    CompanyCreate,
    CompanyCreated,
    CompanyDetail,
    CompanyOut,
    CompanyUpdate,
    CompanyUserOut,
    ResetAdminRequest,
    TemporaryPassword,
)
from app.services.audit import audit

router = APIRouter(prefix="/api/platform", tags=["platform"])


def _slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:50] or "empresa"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug, n = base, 2
    while db.query(Company.id).filter(Company.slug == slug).first() is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


def _counts(db: Session) -> dict[str, dict[int, int]]:
    """Usuarios, proyectos y facturas vigentes por empresa, en tres consultas (no una por empresa)."""

    def grouped(column, *conditions) -> dict[int, int]:
        query = db.query(column, func.count()).group_by(column)
        for condition in conditions:
            query = query.filter(condition)
        return {company_id: n for company_id, n in query.all()}

    return {
        "users": grouped(User.company_id),
        "projects": grouped(Project.company_id),
        "invoices": grouped(Invoice.company_id, Invoice.voided_at.is_(None)),
    }


def _out(company: Company, counts: dict[str, dict[int, int]]) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        name=company.name,
        slug=company.slug,
        is_active=company.is_active,
        notes=company.notes,
        created_at=company.created_at,
        users=counts["users"].get(company.id, 0),
        projects=counts["projects"].get(company.id, 0),
        invoices=counts["invoices"].get(company.id, 0),
    )


def _get_company(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


def _storage_mb(company_id: int) -> float:
    root = Path(get_settings().upload_dir)
    folders = [root / f"c{company_id}"]
    if company_id == 1:  # los archivos anteriores a multi-empresa son de la empresa original
        folders += [root / name for name in ("surveys", "tickets", "logbook", "company")]
    total = sum(f.stat().st_size for folder in folders if folder.is_dir() for f in folder.rglob("*") if f.is_file())
    return round(total / (1024 * 1024), 2)


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), _=Depends(require_platform_admin)):
    counts = _counts(db)
    return [_out(c, counts) for c in db.query(Company).order_by(Company.id).all()]


@router.post("/companies", response_model=CompanyCreated, status_code=status.HTTP_201_CREATED)
def create_company(
    request: Request,
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """Crea la empresa, su membrete, su administrador (con clave temporal que debe cambiar al entrar) y el catálogo
    base de clasificaciones. No hereda nada de otra empresa: ni clientes, ni productos, ni el RNC."""
    if db.query(User.id).filter(User.email == payload.admin_email).first() is not None:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")

    company = Company(name=payload.name, slug=_unique_slug(db, payload.name), notes=payload.notes)
    db.add(company)
    db.flush()  # necesitamos el id para colgarle lo demás
    temporary = secrets.token_urlsafe(9)
    db.add(CompanyProfile(company_id=company.id, name=payload.name))
    db.add(
        User(
            company_id=company.id,
            name=payload.admin_name,
            email=payload.admin_email,
            hashed_password=hash_password(temporary),
            role="admin",
            must_change_password=True,
            created_by=current_user.id,
        )
    )
    audit(
        db,
        "company_created",
        user=current_user,
        company_id=company.id,
        entity="company",
        entity_id=company.id,
        detail={"empresa": payload.name, "admin": payload.admin_email},
        request=request,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Solo el correo repetido (dos altas a la vez) es un error del usuario; cualquier otra causa se deja subir.
        if db.query(User.id).filter(User.email == payload.admin_email).first() is None:
            raise
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")

    with SessionLocal(company_id=company.id) as company_db:  # el catálogo base se siembra DENTRO de la empresa nueva
        seed_new_company(company_db)

    db.refresh(company)
    return CompanyCreated(
        company=_out(company, _counts(db)), admin_email=payload.admin_email, temporary_password=temporary
    )


@router.get("/companies/{company_id}", response_model=CompanyDetail)
def company_detail(company_id: int, db: Session = Depends(get_db), _=Depends(require_platform_admin)):
    company = _get_company(db, company_id)
    team = db.query(User).filter(User.company_id == company_id).order_by(User.role, User.name).all()
    base = _out(company, _counts(db))
    return CompanyDetail(
        **base.model_dump(),
        team=[CompanyUserOut.model_validate(u, from_attributes=True) for u in team],
        storage_mb=_storage_mb(company_id),
    )


@router.put("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    request: Request,
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    company = _get_company(db, company_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        company.name = data["name"].strip()
    if "notes" in data:
        company.notes = data["notes"]
    audit(
        db,
        "company_edited",
        user=current_user,
        company_id=company.id,
        entity="company",
        entity_id=company.id,
        detail={"campos": sorted(data)},
        request=request,
    )
    db.commit()
    return _out(company, _counts(db))


def _set_active(
    request: Request, db: Session, company_id: int, current_user: User, active: bool
) -> CompanyOut:
    company = _get_company(db, company_id)
    if not active and company.id == current_user.company_id:
        raise HTTPException(status_code=400, detail="No puedes suspender tu propia empresa: te quedarías sin acceso")
    if company.is_active != active:
        company.is_active = active
        if not active:
            # Una empresa suspendida pierde el acceso al instante: se cierran todas sus sesiones.
            for user_id in [u for (u,) in db.query(User.id).filter(User.company_id == company.id).all()]:
                revoke_all_refresh_tokens(db, user_id)
        audit(
            db,
            "company_activated" if active else "company_suspended",
            user=current_user,
            company_id=company.id,
            entity="company",
            entity_id=company.id,
            detail={"empresa": company.name},
            request=request,
        )
        db.commit()
    return _out(company, _counts(db))


@router.post("/companies/{company_id}/suspend", response_model=CompanyOut)
def suspend_company(
    request: Request,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    return _set_active(request, db, company_id, current_user, False)


@router.post("/companies/{company_id}/activate", response_model=CompanyOut)
def activate_company(
    request: Request,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    return _set_active(request, db, company_id, current_user, True)


@router.post("/companies/{company_id}/reset-admin-password", response_model=TemporaryPassword)
def reset_admin_password(
    request: Request,
    company_id: int,
    payload: ResetAdminRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """Clave temporal nueva para el administrador de una empresa (por si la perdió). Se muestra una sola vez."""
    _get_company(db, company_id)
    query = db.query(User).filter(User.company_id == company_id, User.role == "admin")
    if payload and payload.user_id is not None:
        query = query.filter(User.id == payload.user_id)
    else:
        query = query.filter(User.is_active.is_(True)).order_by(User.id)
    admin = query.first()
    if admin is None:
        raise HTTPException(status_code=404, detail="Esa empresa no tiene un administrador con ese dato")
    if admin.id == current_user.id:
        raise HTTPException(status_code=400, detail="Para tu propia contraseña usa tu perfil")
    temporary = secrets.token_urlsafe(9)
    admin.hashed_password = hash_password(temporary)
    admin.must_change_password = True
    revoke_all_refresh_tokens(db, admin.id)
    audit(
        db,
        "password_reset_by_platform",
        user=current_user,
        company_id=company_id,
        entity="user",
        entity_id=admin.id,
        detail={"objetivo": admin.email},
        request=request,
    )
    db.commit()
    return TemporaryPassword(user_id=admin.id, email=admin.email, temporary_password=temporary)
