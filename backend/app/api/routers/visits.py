from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.models.visit import VISIT_STATUSES, Visit
from app.schemas.visit import VisitCreate, VisitOut, VisitPunch, VisitUpdate
from app.services.access import can_see_project, project_scope

router = APIRouter(prefix="/api/visits", tags=["visits"])

# Mismo esquema de permisos que Tickets: los tres roles pueden agendar/ver/actualizar —
# un técnico también puede agendar su propia visita o marcarla completada.
allowed_roles = require_role("admin", "oficina", "tecnico")


def _base_query(db: Session):
    return db.query(Visit).options(
        joinedload(Visit.project).joinedload(Project.client), joinedload(Visit.technician)
    )


def _check_technician_exists(db: Session, technician_id: int | None) -> None:
    if technician_id is None:
        return
    technician = db.get(User, technician_id)
    if technician is None:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    if not technician.is_active:
        # Una visita asignada a una cuenta desactivada nadie la va a ver ni a atender.
        raise HTTPException(status_code=400, detail="Ese usuario está desactivado: elige otro técnico")


@router.get("", response_model=list[VisitOut])
def list_visits(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    query = _base_query(db)
    scope = project_scope(current_user)
    if scope is not None:  # técnico: sus visitas y las de sus proyectos
        query = query.filter(or_(Visit.technician_id == current_user.id, Visit.project_id.in_(select(Project.id).where(scope))))
    if start is not None:
        query = query.filter(Visit.scheduled_date >= start)
    if end is not None:
        query = query.filter(Visit.scheduled_date <= end)
    return query.order_by(Visit.scheduled_date, Visit.scheduled_time).all()


@router.post("", response_model=VisitOut, status_code=status.HTTP_201_CREATED)
def create_visit(payload: VisitCreate, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    project = db.get(Project, payload.project_id)
    if project is None or not can_see_project(db, current_user, payload.project_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    _check_technician_exists(db, payload.technician_id)

    visit = Visit(**payload.model_dump(), created_by=current_user.id)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return _base_query(db).filter(Visit.id == visit.id).one()


@router.put("/{visit_id}", response_model=VisitOut)
def update_visit(visit_id: int, payload: VisitUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="Visita no encontrada")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in VISIT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {data['status']}")
    if "technician_id" in data:
        _check_technician_exists(db, data["technician_id"])

    for field, value in data.items():
        setattr(visit, field, value)

    db.commit()
    db.refresh(visit)
    return _base_query(db).filter(Visit.id == visit.id).one()


def _punch_context(db: Session, visit_id: int, current_user: User) -> Visit:
    """La visita sobre la que se marca entrada o salida. Solo la persona asignada marca (o cualquiera si aún no
    hay nadie asignado: quien llega al sitio se queda con la visita). Oficina y admin pueden marcar por otro."""
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    if (
        current_user.role == "tecnico"
        and visit.technician_id is not None
        and visit.technician_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Esta visita está asignada a otro técnico")
    return visit


@router.post("/{visit_id}/checkin", response_model=VisitOut)
def check_in(
    visit_id: int,
    payload: VisitPunch | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    """El técnico llegó al sitio: guarda la hora (y el GPS si lo dio) y la visita pasa a «en sitio»."""
    visit = _punch_context(db, visit_id, current_user)
    if visit.status != "programada":
        raise HTTPException(status_code=400, detail="Esta visita ya no está pendiente de entrada")
    visit.checkin_at = datetime.now(timezone.utc)
    visit.checkin_lat = payload.lat if payload else None
    visit.checkin_lng = payload.lng if payload else None
    visit.status = "en_sitio"
    if visit.technician_id is None:
        visit.technician_id = current_user.id
    db.commit()
    return _base_query(db).filter(Visit.id == visit.id).one()


@router.post("/{visit_id}/checkout", response_model=VisitOut)
def check_out(
    visit_id: int,
    payload: VisitPunch | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    """El técnico terminó: guarda la hora de salida y la visita queda completada."""
    visit = _punch_context(db, visit_id, current_user)
    if visit.status != "en_sitio":
        raise HTTPException(status_code=400, detail="Primero marca la entrada")
    visit.checkout_at = datetime.now(timezone.utc)
    visit.checkout_lat = payload.lat if payload else None
    visit.checkout_lng = payload.lng if payload else None
    visit.status = "completada"
    db.commit()
    return _base_query(db).filter(Visit.id == visit.id).one()
