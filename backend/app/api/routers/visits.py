from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.models.visit import VISIT_STATUSES, Visit
from app.schemas.visit import VisitCreate, VisitOut, VisitUpdate

router = APIRouter(prefix="/api/visits", tags=["visits"])

# Mismo esquema de permisos que Tickets: los tres roles pueden agendar/ver/actualizar —
# un técnico también puede agendar su propia visita o marcarla completada.
allowed_roles = require_role("admin", "oficina", "tecnico")


def _base_query(db: Session):
    return db.query(Visit).options(
        joinedload(Visit.project).joinedload(Project.client), joinedload(Visit.technician)
    )


@router.get("", response_model=list[VisitOut])
def list_visits(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    query = _base_query(db)
    if start is not None:
        query = query.filter(Visit.scheduled_date >= start)
    if end is not None:
        query = query.filter(Visit.scheduled_date <= end)
    return query.order_by(Visit.scheduled_date, Visit.scheduled_time).all()


@router.post("", response_model=VisitOut, status_code=status.HTTP_201_CREATED)
def create_visit(payload: VisitCreate, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

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

    for field, value in data.items():
        setattr(visit, field, value)

    db.commit()
    db.refresh(visit)
    return _base_query(db).filter(Visit.id == visit.id).one()
