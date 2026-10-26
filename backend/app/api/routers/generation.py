from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.routers.ai import _get_project, run_generation
from app.core.quota import ai_quota
from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.services import generation_jobs
from app.services.access import can_see_project

# La generación corre en el servidor y la pantalla solo la consulta: ver services/generation_jobs.py. Va en un router
# aparte del de IA porque consultar el estado cada pocos segundos no debe gastar la cuota de llamadas a la IA.
router = APIRouter(tags=["ai"])

allowed_roles = require_role("admin", "oficina", "tecnico")


@router.post(
    "/api/projects/{project_id}/generate-from-survey/start",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(ai_quota)],
)
def start_generation(
    project_id: int,
    background_engineering: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    """Arranca la generación de la cotización y responde enseguida. Si ya hay una en marcha para el proyecto, se une
    a ella (no se crea una segunda cotización). La app consulta `/status` hasta que termine."""
    project = _get_project(db, project_id)
    label = project.client.name
    user_id = current_user.id

    def runner(job_db: Session) -> dict:
        return run_generation(job_db, project_id, user_id, background_engineering).model_dump(mode="json")

    job, _created = generation_jobs.start(project_id, user_id, current_user.company_id, label, runner)
    return generation_jobs.to_dict(job)


@router.get("/api/projects/{project_id}/generate-from-survey/status")
def generation_status(
    project_id: int, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)
):
    _get_project(db, project_id)  # 404 si el proyecto es de otra empresa: el resultado de la IA no se filtra entre empresas
    job = generation_jobs.get(project_id)
    if job is None:
        return {"project_id": project_id, "status": "none"}
    return generation_jobs.to_dict(job)


@router.get("/api/ai/generation-jobs")
def my_generation_jobs(db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    """Las generaciones de este usuario en marcha o terminadas hace poco. La app lo pregunta al abrirse o al volver
    de otra aplicación, para mostrar el avance o el resultado aunque la página se haya recargado."""
    jobs = [j for j in generation_jobs.for_user(current_user.id) if can_see_project(db, current_user, j.project_id)]
    return [generation_jobs.to_dict(j) for j in jobs]
