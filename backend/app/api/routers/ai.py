from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.budget import Budget
from app.models.engineering import Engineering
from app.models.logbook import LogEntry
from app.models.material import Material
from app.models.product import Product
from app.models.project import Project
from app.models.quote import Quote
from app.models.survey import Survey
from app.models.ticket import Ticket
from app.schemas.ai import AskRequest, AskResponse, BudgetSuggestionOut, EngineeringDraftOut
from app.schemas.survey import SurveyOut
from app.services.ai_client import answer_question, draft_engineering, suggest_budget_items, summarize_survey
from app.services.embeddings import reindex_project, search_projects

router = APIRouter(tags=["ai"])

allowed_roles = require_role("admin", "oficina")


def _get_project(db: Session, project_id: int) -> Project:
    project = db.query(Project).options(joinedload(Project.client)).filter(Project.id == project_id).one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


def _build_project_context(db: Session, project: Project) -> str:
    """Arma un resumen legible del expediente del proyecto para dárselo a la IA como contexto."""
    lines = [
        f"Proyecto {project.code} — estado: {project.status}",
        f"Cliente: {project.client.name}" + (f" ({project.client.company})" if project.client.company else ""),
        f"Descripción: {project.description or '(sin descripción)'}",
    ]

    survey = db.query(Survey).filter(Survey.project_id == project.id).one_or_none()
    if survey:
        lines.append("\n== Levantamiento ==")
        lines.append(f"Notas: {survey.notes or '-'}")
        lines.append(f"Medidas: {survey.measurements or '-'}")
        lines.append(f"Observaciones: {survey.observations or '-'}")
        if survey.ai_summary:
            lines.append(f"Resumen IA previo: {survey.ai_summary}")

    engineering = db.query(Engineering).filter(Engineering.project_id == project.id).one_or_none()
    if engineering and any(
        [
            engineering.recommended_equipment,
            engineering.distribution,
            engineering.conduits,
            engineering.wiring,
            engineering.technical_design,
        ]
    ):
        lines.append("\n== Ingeniería ==")
        lines.append(f"Equipos recomendados: {engineering.recommended_equipment or '-'}")
        lines.append(f"Distribución: {engineering.distribution or '-'}")
        lines.append(f"Canalizaciones: {engineering.conduits or '-'}")
        lines.append(f"Cableado: {engineering.wiring or '-'}")
        lines.append(f"Diseño técnico: {engineering.technical_design or '-'}")

    budgets = db.query(Budget).filter(Budget.project_id == project.id).all()
    if budgets:
        lines.append("\n== Presupuestos ==")
        for b in budgets:
            lines.append(f"{b.code}: total RD$ {b.total}")

    quotes = db.query(Quote).filter(Quote.project_id == project.id).all()
    if quotes:
        lines.append("\n== Cotizaciones ==")
        for q in quotes:
            lines.append(f"{q.code}: estado {q.status}, total RD$ {q.total}")

    materials = db.query(Material).filter(Material.project_id == project.id).all()
    if materials:
        lines.append("\n== Materiales ==")
        for m in materials:
            lines.append(f"{m.quantity} x {m.description} — {m.status}")

    log_entries = db.query(LogEntry).filter(LogEntry.project_id == project.id).order_by(LogEntry.entry_date).all()
    if log_entries:
        lines.append("\n== Bitácora ==")
        for entry in log_entries:
            lines.append(f"{entry.entry_date}: {entry.comment}")

    tickets = db.query(Ticket).filter(Ticket.project_id == project.id).all()
    if tickets:
        lines.append("\n== Tickets de soporte ==")
        for t in tickets:
            lines.append(f"{t.code} ({t.status}): {t.problem}" + (f" → {t.solution}" if t.solution else ""))

    return "\n".join(lines)


def _reindex_quietly(db: Session, project: Project, context: str) -> None:
    """Actualiza el embedding del proyecto para búsqueda semántica; si Ollama no está
    disponible, no debe romper el flujo principal (ingeniería, presupuesto, etc.)."""
    try:
        reindex_project(db, project, context)
    except Exception:
        db.rollback()


@router.post("/api/projects/{project_id}/survey/ai-summarize", response_model=SurveyOut)
def ai_summarize_survey(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    survey = (
        db.query(Survey)
        .options(joinedload(Survey.assets))
        .filter(Survey.project_id == project_id)
        .one_or_none()
    )
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamiento no encontrado")

    photo_paths = [a.file_path for a in survey.assets if a.kind == "photo"]
    summary = summarize_survey(survey.notes or "", survey.measurements or "", survey.observations or "", photo_paths)

    survey.ai_summary = summary
    db.commit()
    db.refresh(survey)
    return survey


@router.post("/api/projects/{project_id}/engineering/ai-draft", response_model=EngineeringDraftOut)
def ai_draft_engineering(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    project = _get_project(db, project_id)
    context = _build_project_context(db, project)
    _reindex_quietly(db, project, context)
    draft = draft_engineering(context)
    return EngineeringDraftOut(**draft)


@router.post("/api/projects/{project_id}/budget-suggestions", response_model=BudgetSuggestionOut)
def ai_budget_suggestions(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    project = _get_project(db, project_id)
    context = _build_project_context(db, project)
    _reindex_quietly(db, project, context)

    products = db.query(Product).all()
    catalog = [{"id": p.id, "name": p.name, "category": p.category} for p in products]
    product_prices = {p.id: float(p.price) for p in products}

    items = suggest_budget_items(context, catalog)
    for item in items:
        if item.get("product_id") is not None:
            item["unit_price"] = product_prices.get(item["product_id"], 0)

    return BudgetSuggestionOut(items=items)


@router.post("/api/ai/ask", response_model=AskResponse)
def ai_ask(payload: AskRequest, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    if payload.project_id is not None:
        project = _get_project(db, payload.project_id)
        context = _build_project_context(db, project)
        _reindex_quietly(db, project, context)
        answer = answer_question(context, payload.question)
        return AskResponse(answer=answer, projects=[project.code])

    # Sin project_id: búsqueda semántica entre todos los proyectos indexados, usando
    # embeddings locales (Ollama + nomic-embed-text) en vez de mandar todo el historial
    # de la empresa al modelo de texto de una vez.
    matches = search_projects(db, payload.question, top_k=3)
    if not matches:
        return AskResponse(
            answer=(
                "Todavía no hay proyectos indexados para búsqueda entre todos los "
                "proyectos. Usa alguna función de IA (organizar levantamiento, generar "
                "propuesta, sugerir materiales o preguntar sobre un proyecto específico) "
                "al menos una vez por proyecto para indexarlo."
            ),
            projects=[],
        )

    combined_context = "\n\n---\n\n".join(_build_project_context(db, project) for project in matches)
    answer = answer_question(combined_context, payload.question)
    return AskResponse(answer=answer, projects=[project.code for project in matches])
