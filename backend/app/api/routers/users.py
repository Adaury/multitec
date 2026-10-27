import secrets
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import active_sessions, hash_password, require_role, revoke_all_refresh_tokens
from app.core.timeutil import today_dr
from app.db.session import get_db
from app.models.company import Company
from app.models.refresh_token import RefreshToken
from app.models.ticket import Ticket
from app.models.user import User
from app.models.visit import Visit
from app.schemas.user import (
    SessionOut,
    TechnicianOut,
    TemporaryPasswordOut,
    UserCreate,
    UserOut,
    UserUpdate,
    WorkloadOut,
)
from app.services.audit import audit
from app.services.reports import OPEN_TICKET_STATUSES

router = APIRouter(prefix="/api/users", tags=["users"])

admin_only = require_role("admin")
allowed_roles = require_role("admin", "oficina", "tecnico")


def _ensure_free_seat(db: Session, company_id: int) -> None:
    """Respeta el tope de usuarios activos que la plataforma le puso a la empresa (si tiene)."""
    company = db.get(Company, company_id)
    if company is None or company.max_users is None:
        return
    active = db.query(User).filter(User.is_active.is_(True)).count()
    if active >= company.max_users:
        raise HTTPException(
            status_code=400,
            detail=f"Tu plan permite hasta {company.max_users} usuarios activos. Desactiva a alguien o pide ampliar el plan.",
        )


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(admin_only)):
    return db.query(User).order_by(User.name).all()


@router.get("/technicians", response_model=list[TechnicianOut])
def list_technicians(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    """Lista liviana (solo id/nombre) para asignar técnico a un ticket — a diferencia de
    GET /api/users (admin-only, expone email/rol/estado), esta la puede llamar cualquier
    rol que gestione tickets."""
    return (
        db.query(User)
        .filter(User.role == "tecnico", User.is_active.is_(True))
        .order_by(User.name)
        .all()
    )


@router.get("/workload", response_model=list[WorkloadOut])
def team_workload(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "oficina")),
):
    """Cuánto trabajo tiene cada técnico activo en un rango (por defecto, hoy): visitas agendadas y hechas,
    tickets abiertos y horas en sitio (de la entrada y salida marcadas). Sirve para repartir el trabajo."""
    first = start or today_dr()
    last = end or first
    users = db.query(User).filter(User.is_active.is_(True), User.role.in_(("tecnico", "admin"))).order_by(User.name).all()
    return [_workload(db, user, first, last) for user in users]


def _workload(db: Session, user: User, first: date, last: date) -> dict:
    visits = (
        db.query(Visit)
        .filter(Visit.technician_id == user.id, Visit.scheduled_date >= first, Visit.scheduled_date <= last)
        .all()
    )
    live = [v for v in visits if v.status != "cancelada"]
    seconds = sum(
        (v.checkout_at - v.checkin_at).total_seconds()
        for v in live
        if v.checkin_at is not None and v.checkout_at is not None
    )
    open_tickets = (
        db.query(Ticket).filter(Ticket.technician_id == user.id, Ticket.status.in_(OPEN_TICKET_STATUSES)).count()
    )
    return {
        "user_id": user.id,
        "name": user.name,
        "visits_total": len(live),
        "visits_pending": sum(1 for v in live if v.status in ("programada", "en_sitio")),
        "visits_done": sum(1 for v in live if v.status == "completada"),
        "open_tickets": open_tickets,
        "hours_on_site": round(seconds / 3600, 2),
    }


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    _ensure_free_seat(db, current_user.company_id)
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        # La contraseña la eligió el admin: el usuario debe cambiarla en su primer ingreso.
        must_change_password=True,
        role=payload.role,
        phone=payload.phone,
        zone=payload.zone,
        skills=payload.skills,
        vehicle=payload.vehicle,
        created_by=current_user.id,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")
    audit(
        db,
        "user_created",
        user=current_user,
        entity="user",
        entity_id=user.id,
        detail={"email": user.email, "role": user.role},
        request=request,
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    request: Request,
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    data = payload.model_dump(exclude_unset=True)

    # Un admin no puede desactivarse ni quitarse el rol admin a sí mismo — evita que el
    # sistema se quede sin ningún admin activo por accidente.
    if user.id == current_user.id:
        if data.get("is_active") is False:
            raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")
        if "role" in data and data["role"] != "admin":
            raise HTTPException(status_code=400, detail="No puedes quitarte el rol admin a ti mismo")

    changes: dict = {}
    if "password" in data:
        password = data.pop("password")
        if password:
            user.hashed_password = hash_password(password)
            # Una contraseña puesta por otro admin es temporal; la propia no.
            user.must_change_password = user.id != current_user.id
            revoke_all_refresh_tokens(db, user.id)
            changes["password"] = "cambiada"  # solo el hecho, nunca el valor

    if data.get("is_active") is False:
        revoke_all_refresh_tokens(db, user.id)
    if data.get("is_active") is True and not user.is_active:
        _ensure_free_seat(db, current_user.company_id)

    # Un correo vacío o nulo no es un cambio: nunca se borra.
    if "email" in data and not data["email"]:
        data.pop("email")

    for field, value in data.items():
        if getattr(user, field) != value:
            # Rol, estado y correo importan para la auditoría; los datos de la ficha solo se anotan como cambiados.
            changes[field] = {"de": getattr(user, field), "a": value} if field in ("role", "is_active", "email") else "editado"
        setattr(user, field, value)

    if changes:
        audit(
            db,
            "password_reset_by_admin" if list(changes) == ["password"] else "user_updated",
            user=current_user,
            entity="user",
            entity_id=user.id,
            detail={"objetivo": user.email, "cambios": changes},
            request=request,
        )

    try:
        db.commit()
    except IntegrityError:
        # El único campo con restricción de unicidad que se puede cambiar aquí es el correo.
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=TemporaryPasswordOut)
def reset_password(
    request: Request, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    """Genera una contraseña temporal aleatoria (se muestra una sola vez, nunca se guarda en claro), cierra
    todas las sesiones de esa persona y la obliga a cambiarla al entrar."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Para tu propia contraseña usa tu perfil")
    temporary = secrets.token_urlsafe(9)  # 12 caracteres, sin ambigüedades de formato
    user.hashed_password = hash_password(temporary)
    user.must_change_password = True
    revoke_all_refresh_tokens(db, user.id)
    audit(
        db,
        "password_reset_by_admin",
        user=current_user,
        entity="user",
        entity_id=user.id,
        detail={"objetivo": user.email},
        request=request,
    )
    db.commit()
    return {"temporary_password": temporary}


@router.get("/{user_id}/sessions", response_model=list[SessionOut])
def list_user_sessions(user_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return active_sessions(db, user_id)


@router.delete("/{user_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_user_session(
    request: Request,
    user_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    session = db.get(RefreshToken, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    session.revoked = True
    audit(db, "session_revoked", user=current_user, entity="user", entity_id=user_id, request=request)
    db.commit()


@router.post("/{user_id}/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all_user_sessions(
    request: Request, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    revoke_all_refresh_tokens(db, user_id)
    audit(db, "sessions_revoked_all", user=current_user, entity="user", entity_id=user_id, request=request)
    db.commit()


@router.get("/{user_id}/workload", response_model=WorkloadOut)
def user_workload(
    user_id: int,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "oficina")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    first = start or today_dr()
    return _workload(db, user, first, end or first)
