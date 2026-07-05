import math

from sqlalchemy.orm import Session

from app.ai_engine.ollama_client import get_client
from app.core.config import get_settings
from app.models.embedding import ProjectEmbedding
from app.models.project import Project


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    client = get_client()
    response = client.embed(model=settings.ai_embedding_model, input=text[:8000])
    return list(response.embeddings[0])


def reindex_project(db: Session, project: Project, context: str) -> None:
    """Recalcula y guarda el embedding del expediente de un proyecto. Se llama cada vez
    que se arma el contexto de un proyecto para la IA (ai-summarize, ai-draft,
    budget-suggestions, ask de un solo proyecto), así los embeddings se mantienen
    razonablemente al día sin necesitar un job aparte."""
    vector = embed_text(context)
    row = db.get(ProjectEmbedding, project.id)
    if row is None:
        row = ProjectEmbedding(project_id=project.id, embedding=vector)
        db.add(row)
    else:
        row.embedding = vector
    db.commit()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_projects(db: Session, question: str, top_k: int = 3) -> list[Project]:
    """Busca los proyectos más relevantes para una pregunta en lenguaje natural,
    comparando el embedding de la pregunta contra el embedding guardado de cada
    proyecto. Los proyectos sin embedding (nunca indexados) se omiten — se indexan la
    primera vez que se usa alguna función de IA sobre ellos."""
    rows = db.query(ProjectEmbedding).all()
    if not rows:
        return []

    question_vector = embed_text(question)
    scored = [(_cosine_similarity(question_vector, row.embedding), row.project_id) for row in rows]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    top_ids = [project_id for _, project_id in scored[:top_k]]

    projects = db.query(Project).filter(Project.id.in_(top_ids)).all()
    projects_by_id = {p.id: p for p in projects}
    return [projects_by_id[pid] for pid in top_ids if pid in projects_by_id]
