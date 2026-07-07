"""Motor 7 — análisis periódico (§ docs/ai-engine-architecture.md, "Scoping del análisis
periódico"). Las dos consultas de detección que ese scoping fijó, y solo esas dos: no
agregan patrones, no crean/borran nada — devuelven candidatos de solo lectura con su
evidencia para que un administrador decida, igual que ya hace con las cotizaciones
pendientes.

`min_projects`/`min_ratio` son los umbrales que el scoping dejó deliberadamente sin fijar
por falta de datos reales para calibrarlos; los defaults aquí son un punto de partida
razonable, no un valor probado, y se pueden pasar explícitos en cuanto haya evidencia de
qué tan sensible/ruidoso resulta cada patrón en la práctica.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import median

from sqlalchemy.orm import Session

from app.models.ai_feedback_event import (
    ENTITY_TYPE_BUDGET_ITEM,
    ORIGIN_HUMAN_ADDED,
    ORIGIN_HUMAN_REMOVED,
    AIFeedbackEvent,
)
from app.models.budget import Budget, BudgetItem
from app.models.catalog_rule import CatalogRule
from app.models.product import Product
from app.models.project import Project
from app.models.technical_rule import ACTION_TYPE_ADD_ACCESSORY, TechnicalRule

DEFAULT_MIN_PROJECTS = 3
DEFAULT_MIN_RATIO = 0.5


@dataclass
class AccessoryCandidate:
    """Patrón 1 — un producto se agregó a mano de forma consistente cuando otro (la
    fuente) estaba presente, sin que ninguna regla lo cubra todavía. Candidato a
    `add_accessory` nuevo; `suggested_target_tag` es un punto de partida para prellenar
    el formulario existente, no algo que se envía sin que un admin lo confirme."""

    source_product_id: int
    source_product_name: str
    added_product_id: int
    added_product_name: str
    suggested_target_tag: str | None
    project_count: int
    total_projects_with_source: int
    ratio: float
    example_quantity: float
    example_project_codes: list[str] = field(default_factory=list)


@dataclass
class StaleRuleCandidate:
    """Patrón 2 — una `TechnicalRule` `add_accessory` ya existente cuyo accesorio se
    quita a mano de forma consistente. Candidato a revisar/borrar esa regla; no se borra
    sola, solo se resalta con su evidencia."""

    rule_id: int
    source_product_id: int
    source_product_name: str
    target_tag: str
    would_add_product_id: int | None
    would_add_product_name: str | None
    removed_count: int
    total_projects_with_source: int
    ratio: float
    example_project_codes: list[str] = field(default_factory=list)


def _existing_accessory_coverage(db: Session) -> dict[int, set[str]]:
    """source_product_id -> tags ya cubiertos por una regla add_accessory (nueva o
    legacy) — para no proponer de nuevo algo que ya se puede generar automáticamente."""
    coverage: dict[int, set[str]] = defaultdict(set)
    for source_id, tag in db.query(CatalogRule.source_product_id, CatalogRule.target_tag).all():
        coverage[source_id].add(tag)
    technical_rules = db.query(TechnicalRule).filter(TechnicalRule.action_type == ACTION_TYPE_ADD_ACCESSORY).all()
    for rule in technical_rules:
        if rule.target_tag:
            coverage[rule.source_product_id].add(rule.target_tag)
    return coverage


def _project_codes(db: Session, project_ids: set[int], limit: int = 5) -> list[str]:
    if not project_ids:
        return []
    rows = (
        db.query(Project.code)
        .filter(Project.id.in_(sorted(project_ids)[:limit]))
        .order_by(Project.code)
        .all()
    )
    return [code for (code,) in rows]


def detect_accessory_candidates(
    db: Session, min_projects: int = DEFAULT_MIN_PROJECTS, min_ratio: float = DEFAULT_MIN_RATIO
) -> list[AccessoryCandidate]:
    """Patrón 1 (§ scoping): agrupa eventos `human_added` por (producto fuente presente
    en el mismo presupuesto, producto agregado a mano) y propone un `add_accessory` para
    los pares que se repiten en suficientes proyectos distintos y no tienen ya una regla
    que los cubra."""
    events = (
        db.query(AIFeedbackEvent)
        .filter(
            AIFeedbackEvent.entity_type == ENTITY_TYPE_BUDGET_ITEM,
            AIFeedbackEvent.origin == ORIGIN_HUMAN_ADDED,
            AIFeedbackEvent.budget_id.isnot(None),
            AIFeedbackEvent.product_id.isnot(None),
        )
        .all()
    )
    if not events:
        return []

    budget_ids = {e.budget_id for e in events}
    items_by_budget: dict[int, set[int]] = defaultdict(set)
    for budget_id, product_id in (
        db.query(BudgetItem.budget_id, BudgetItem.product_id).filter(BudgetItem.budget_id.in_(budget_ids)).all()
    ):
        if product_id is not None:
            items_by_budget[budget_id].add(product_id)

    budget_project = dict(db.query(Budget.id, Budget.project_id).filter(Budget.id.in_(budget_ids)).all())

    pair_projects: dict[tuple[int, int], set[int]] = defaultdict(set)
    pair_quantities: dict[tuple[int, int], list[float]] = defaultdict(list)
    for event in events:
        added_id = event.product_id
        project_id = budget_project.get(event.budget_id)
        if project_id is None:
            continue
        sources = items_by_budget.get(event.budget_id, set()) - {added_id}
        quantity = None
        if event.new_value:
            try:
                quantity = float(event.new_value)
            except ValueError:
                quantity = None
        for source_id in sources:
            pair_projects[(source_id, added_id)].add(project_id)
            if quantity is not None:
                pair_quantities[(source_id, added_id)].append(quantity)

    if not pair_projects:
        return []

    all_source_ids = {source_id for source_id, _ in pair_projects}
    total_projects_with_source: dict[int, set[int]] = defaultdict(set)
    for product_id, project_id in (
        db.query(BudgetItem.product_id, Budget.project_id)
        .join(Budget, Budget.id == BudgetItem.budget_id)
        .filter(BudgetItem.product_id.in_(all_source_ids))
        .all()
    ):
        total_projects_with_source[product_id].add(project_id)

    coverage = _existing_accessory_coverage(db)
    all_product_ids = {pid for pair in pair_projects for pid in pair}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(all_product_ids)).all()}

    candidates: list[AccessoryCandidate] = []
    for (source_id, added_id), project_ids in pair_projects.items():
        count = len(project_ids)
        if count < min_projects:
            continue
        total = len(total_projects_with_source.get(source_id, set())) or count
        ratio = count / total
        if ratio < min_ratio:
            continue

        added_product = products.get(added_id)
        added_tags = (added_product.tags or []) if added_product else []
        if coverage.get(source_id, set()) & set(added_tags):
            continue  # ya hay una regla que cubre alguno de estos tags para esta fuente

        source_product = products.get(source_id)
        quantities = pair_quantities.get((source_id, added_id)) or [1.0]
        candidates.append(
            AccessoryCandidate(
                source_product_id=source_id,
                source_product_name=source_product.name if source_product else f"#{source_id}",
                added_product_id=added_id,
                added_product_name=added_product.name if added_product else f"#{added_id}",
                suggested_target_tag=added_tags[0] if added_tags else None,
                project_count=count,
                total_projects_with_source=total,
                ratio=ratio,
                example_quantity=median(quantities),
                example_project_codes=_project_codes(db, project_ids),
            )
        )

    candidates.sort(key=lambda c: (-c.project_count, -c.ratio))
    return candidates


def detect_stale_rule_candidates(
    db: Session, min_projects: int = DEFAULT_MIN_PROJECTS, min_ratio: float = DEFAULT_MIN_RATIO
) -> list[StaleRuleCandidate]:
    """Patrón 2 (§ scoping): para cada `TechnicalRule` `add_accessory` activa, cuenta en
    cuántos proyectos donde el producto fuente está presente el accesorio que la regla
    generaría terminó quitado a mano. Una proporción alta sugiere revisar o borrar esa
    regla — no se borra sola."""
    rules = db.query(TechnicalRule).filter(TechnicalRule.action_type == ACTION_TYPE_ADD_ACCESSORY).all()
    if not rules:
        return []

    # Mismo orden que compute_survey_items/expand_with_rules: el primer producto del
    # catálogo (por código) cuyos tags contengan el target_tag es el que la regla
    # agregaría hoy.
    products = db.query(Product).order_by(Product.code).all()
    product_by_id = {p.id: p for p in products}

    candidates: list[StaleRuleCandidate] = []
    for rule in rules:
        target_tag = rule.target_tag
        if not target_tag:
            continue
        source_id = rule.source_product_id

        source_rows = (
            db.query(BudgetItem.budget_id, Budget.project_id)
            .join(Budget, Budget.id == BudgetItem.budget_id)
            .filter(BudgetItem.product_id == source_id)
            .all()
        )
        if not source_rows:
            continue
        budgets_with_source = {budget_id for budget_id, _ in source_rows}
        projects_with_source = {project_id for _, project_id in source_rows}

        would_add = next((p for p in products if target_tag in (p.tags or [])), None)
        if would_add is not None:
            # Igual que expand_with_rules: la regla siempre agrega este producto exacto
            # (el primero del catálogo, por código, con este tag) — solo sus remociones
            # cuentan como evidencia contra esta regla.
            tagged_ids = {would_add.id}
        else:
            # Ningún producto del catálogo tiene hoy este tag (pudo quitarse después de
            # crear la regla) — sin un candidato exacto, se usa cualquier producto con el
            # tag como señal de respaldo.
            tagged_ids = {p.id for p in products if target_tag in (p.tags or [])}

        removed_events = (
            db.query(AIFeedbackEvent)
            .filter(
                AIFeedbackEvent.entity_type == ENTITY_TYPE_BUDGET_ITEM,
                AIFeedbackEvent.origin == ORIGIN_HUMAN_REMOVED,
                AIFeedbackEvent.budget_id.in_(budgets_with_source),
                AIFeedbackEvent.product_id.in_(tagged_ids),
            )
            .all()
            if tagged_ids
            else []
        )
        if not removed_events:
            continue

        removed_budget_ids = {e.budget_id for e in removed_events}
        removed_project_ids = {
            project_id
            for budget_id, project_id in db.query(Budget.id, Budget.project_id)
            .filter(Budget.id.in_(removed_budget_ids))
            .all()
        }

        count = len(removed_project_ids)
        if count < min_projects:
            continue
        total = len(projects_with_source) or count
        ratio = count / total
        if ratio < min_ratio:
            continue

        source_product = product_by_id.get(source_id)
        candidates.append(
            StaleRuleCandidate(
                rule_id=rule.id,
                source_product_id=source_id,
                source_product_name=source_product.name if source_product else f"#{source_id}",
                target_tag=target_tag,
                would_add_product_id=would_add.id if would_add else None,
                would_add_product_name=would_add.name if would_add else None,
                removed_count=count,
                total_projects_with_source=total,
                ratio=ratio,
                example_project_codes=_project_codes(db, removed_project_ids),
            )
        )

    candidates.sort(key=lambda c: (-c.removed_count, -c.ratio))
    return candidates
