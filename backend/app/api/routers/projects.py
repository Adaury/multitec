from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.engineering import Engineering
from app.models.project import Project
from app.models.survey import Survey
from app.models.user import User
from app.schemas.margin import MarginSummary
from app.schemas.project import ProjectCreate, ProjectDetailOut, ProjectOut, ProjectUpdate
from app.services.code_generator import next_code
from app.services.csv_export import build_csv
from app.services.execution import ensure_stages
from app.services.margin import project_margin

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Técnico puede ver proyectos (para saber en qué trabajar) pero no crear/editar —
# eso es responsabilidad de oficina/admin.
allowed_roles = require_role("admin", "oficina", "tecnico")
write_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(write_roles)):
    code = next_code(db, "PRY")
    data = payload.model_dump(exclude_unset=True)
    project = Project(code=code, created_by=current_user.id, **data)
    db.add(project)
    db.flush()

    # Cada proyecto nace con su levantamiento e ingeniería vacíos (núcleo del ERP)
    db.add(Survey(project_id=project.id, created_by=current_user.id))
    db.add(Engineering(project_id=project.id, created_by=current_user.id))
    ensure_stages(db, project)

    db.commit()
    db.refresh(project)
    return project


@router.get("/export")
def export_projects_csv(db: Session = Depends(get_db), _=Depends(write_roles)):
    projects = (
        db.query(Project)
        .options(joinedload(Project.client))
        .order_by(Project.created_at.desc())
        .all()
    )
    headers = ["Código", "Cliente", "Estado", "Fecha", "Descripción"]
    rows = [
        [p.code, p.client.name, p.status, p.date.isoformat(), p.description or ""]
        for p in projects
    ]
    csv_bytes = build_csv(headers, rows)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="proyectos.csv"'},
    )


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    project = (
        db.query(Project)
        .options(joinedload(Project.client))
        .filter(Project.id == project_id)
        .one_or_none()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.get("/{project_id}/margin", response_model=MarginSummary)
def get_project_margin(project_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project_margin(db, project_id)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), _=Depends(write_roles)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project
