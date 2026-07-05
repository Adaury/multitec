import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.ai_engine.calculation import CABLE_WASTE_MARGIN_KEY, apply_cable_waste_margin, get_calculation_parameter
from app.ai_engine.catalog_matching import suggest_budget_items
from app.ai_engine.documents import draft_engineering
from app.ai_engine.nlu import summarize_survey
from app.ai_engine.qa import answer_question
from app.ai_engine.rules import build_accessory_rule_dicts, expand_with_rules
from app.api.routers.budgets import build_budget, build_quote_from_budget
from app.core.security import require_role
from app.db.session import get_db
from app.models.budget import Budget
from app.models.catalog_rule import CatalogRule
from app.models.engineering import Engineering
from app.models.logbook import LogEntry
from app.models.material import Material
from app.models.product import Product
from app.models.project import Project
from app.models.quote import Quote
from app.models.survey import Survey
from app.models.technical_rule import TechnicalRule
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ai import AskRequest, AskResponse, BudgetSuggestionOut, EngineeringDraftOut, GenerateFromSurveyOut
from app.schemas.budget import BudgetItemIn
from app.schemas.survey import SurveyOut
from app.services.embeddings import reindex_project, search_projects
from app.services.notifications import notify_quote_pending

router = APIRouter(tags=["ai"])

logger = logging.getLogger("multitec.ai")

allowed_roles = require_role("admin", "oficina", "tecnico")


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


def _build_catalog_dicts(products: list[Product]) -> list[dict]:
    """Catálogo enriquecido con los campos semánticos (§ catálogo inteligente) para que
    suggest_budget_items pueda hacer matching por tags/sinónimos y proponer accesorios
    relacionados, en vez de depender solo del nombre exacto. `products` debe venir ordenado
    por código — expand_with_rules resuelve el primer match del catálogo en ese orden."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category_name,
            "unit": p.unit,
            "tags": p.tags or [],
            "synonyms": p.synonyms or [],
        }
        for p in products
    ]


def _reindex_quietly(db: Session, project: Project, context: str) -> None:
    """Actualiza el embedding del proyecto para búsqueda semántica; si Ollama no está
    disponible, no debe romper el flujo principal (ingeniería, presupuesto, etc.)."""
    try:
        reindex_project(db, project, context)
    except Exception:
        db.rollback()
        logger.exception("No se pudo actualizar el embedding del proyecto %s", project.id)


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

    products = db.query(Product).order_by(Product.code).all()
    catalog = _build_catalog_dicts(products)
    rules = build_accessory_rule_dicts(db.query(CatalogRule).all(), db.query(TechnicalRule).all())
    product_prices = {p.id: float(p.price) for p in products}

    items = suggest_budget_items(context, catalog)
    items = expand_with_rules(items, catalog, rules)
    items = apply_cable_waste_margin(items, catalog, get_calculation_parameter(db, CABLE_WASTE_MARGIN_KEY))
    for item in items:
        if item.get("product_id") is not None:
            item["unit_price"] = product_prices.get(item["product_id"], 0)

    return BudgetSuggestionOut(items=items)


@router.post("/api/projects/{project_id}/generate-from-survey", response_model=GenerateFromSurveyOut)
def generate_from_survey(
    project_id: int, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)
):
    """Genera Presupuesto + Cotización (y, si aplica, un borrador de Ingeniería) de una
    sola vez a partir del levantamiento — § levantamiento inteligente. La cotización queda
    'pendiente': aprobar sigue siendo una decisión humana (staff u oficina, o el cliente
    desde el portal), no se auto-aprueba aquí."""
    project = _get_project(db, project_id)
    context = _build_project_context(db, project)
    _reindex_quietly(db, project, context)

    products = db.query(Product).order_by(Product.code).all()
    catalog = _build_catalog_dicts(products)
    rules = build_accessory_rule_dicts(db.query(CatalogRule).all(), db.query(TechnicalRule).all())
    product_prices = {p.id: float(p.price) for p in products}

    items = suggest_budget_items(context, catalog)
    items = expand_with_rules(items, catalog, rules)
    if not items:
        raise HTTPException(status_code=400, detail="La IA no pudo derivar materiales del levantamiento")

    items = apply_cable_waste_margin(items, catalog, get_calculation_parameter(db, CABLE_WASTE_MARGIN_KEY))
    for item in items:
        if item.get("product_id") is not None:
            item["unit_price"] = product_prices.get(item["product_id"], 0)

    items_in = [BudgetItemIn(**item) for item in items]
    budget = build_budget(
        db, project_id, "Generado automáticamente desde el levantamiento", items_in, current_user.id
    )
    db.flush()  # build_quote_from_budget necesita budget.id
    quote = build_quote_from_budget(db, budget, current_user.id)

    # El borrador de ingeniería es "best effort": si esta segunda llamada a Ollama falla,
    # la cotización ya generada no se pierde. Solo se rellena si el proyecto no tiene
    # ingeniería propia todavía (no pisa lo que oficina ya haya editado a mano).
    engineering_drafted = False
    engineering = db.query(Engineering).filter(Engineering.project_id == project_id).one_or_none()
    if engineering is not None and not any(
        [
            engineering.recommended_equipment,
            engineering.distribution,
            engineering.conduits,
            engineering.wiring,
            engineering.technical_design,
            engineering.observations,
        ]
    ):
        try:
            draft = draft_engineering(context)
            engineering.recommended_equipment = draft["recommended_equipment"]
            engineering.distribution = draft["distribution"]
            engineering.conduits = draft["conduits"]
            engineering.wiring = draft["wiring"]
            engineering.technical_design = draft["technical_design"]
            engineering.observations = draft["observations"]
            engineering_drafted = True
        except HTTPException as e:
            logger.warning("Borrador de ingeniería omitido para el proyecto %s: %s", project_id, e.detail)

    db.commit()
    db.refresh(budget)
    db.refresh(quote)
    notify_quote_pending(db, quote)
    return GenerateFromSurveyOut(budget=budget, quote=quote, engineering_drafted=engineering_drafted)


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
