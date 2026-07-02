from app.models.execution import STAGE_NAMES, ProjectStage
from app.models.project import Project


def ensure_stages(db, project: Project) -> None:
    """Crea las 5 etapas fijas de ejecución si el proyecto aún no las tiene."""
    existing = {stage.name for stage in project.stages}
    for order, name in enumerate(STAGE_NAMES):
        if name not in existing:
            db.add(ProjectStage(project_id=project.id, name=name, order=order))


def stage_progress(stages: list[ProjectStage]) -> float:
    if not stages:
        return 0.0
    completed = sum(1 for s in stages if s.completed)
    return round(completed / len(stages) * 100, 2)
