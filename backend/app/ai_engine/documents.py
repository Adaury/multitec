"""Motor 6 — Motor de generación documental (§ docs/ai-engine-architecture.md).

`generate_documents_from_survey` es el orquestador que generaliza lo que antes vivía
inline dentro de `api/routers/ai.py::generate_from_survey`: corre el pipeline completo de
Motor 1 (interpretar) → Motor 2 (resolver contra catálogo) → Motor 4 (reglas) → Motor 5
(calculadoras) y arma Presupuesto + Cotización + un borrador de Ingeniería best-effort.
`compute_survey_items` es la parte de ese pipeline que no persiste nada — la comparten
esta función y la vista previa (`ai_budget_suggestions`), que antes la tenía duplicada.

Ninguna de las dos funciones comitea ni notifica — igual que `build_budget`/
`build_quote_from_budget` (`api/routers/budgets.py`), que también usan: el caller (el
router) decide cuándo comitear y cuándo disparar efectos secundarios como notificaciones.
"""

import json
import logging
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai_engine.calculation import (
    CABLE_WASTE_MARGIN_KEY,
    LABOR_HOURLY_RATE_KEY,
    LABOR_MAX_HOURS_PER_TECHNICIAN_KEY,
    STORAGE_GB_PER_MP_PER_DAY_KEY,
    STORAGE_RETENTION_DAYS_KEY,
    apply_cable_waste_margin,
    build_labor_budget_item,
    calculate_capacity_warnings,
    calculate_labor,
    calculate_storage,
    get_calculation_parameter,
)
from app.ai_engine.catalog_matching import suggest_budget_items
from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.ai_engine.rules import (
    build_accessory_rule_dicts,
    expand_with_rules,
    resolve_calculation_parameter_overrides,
    resolve_engineering_notes,
)
from app.api.routers.budgets import build_budget, build_quote_from_budget
from app.core.config import get_settings
from app.models.budget import Budget
from app.models.catalog_rule import CatalogRule
from app.models.engineering import Engineering
from app.models.product import Product
from app.models.quote import Quote
from app.models.technical_rule import TechnicalRule
from app.schemas.budget import BudgetItemIn

logger = logging.getLogger("multitec.ai")

ENGINEERING_SCHEMA = {
    "type": "object",
    "properties": {
        "recommended_equipment": {"type": "string"},
        "distribution": {"type": "string"},
        "conduits": {"type": "string"},
        "wiring": {"type": "string"},
        "technical_design": {"type": "string"},
        "observations": {"type": "string"},
    },
    "required": [
        "recommended_equipment",
        "distribution",
        "conduits",
        "wiring",
        "technical_design",
        "observations",
    ],
}


def draft_engineering(project_context: str) -> dict:
    settings = get_settings()
    client = get_client()

    prompt = (
        "Eres un ingeniero de sistemas de seguridad electrónica. A partir del siguiente "
        "expediente de proyecto, redacta un borrador de ingeniería técnica en español. "
        "Sé concreto y práctico; si falta información para alguna sección, indícalo "
        "brevemente en vez de inventar.\n\n" + project_context
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=ENGINEERING_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options=OLLAMA_OPTIONS,
        )
        return json.loads(response.message.content)

    return _call(run)


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


def _build_install_profiles(products: list[Product]) -> dict[int, tuple[float | None, str | None]]:
    """product_id -> (install_minutes, labor_role) para `calculate_labor` (Motor 5)."""
    return {
        p.id: (float(p.install_minutes) if p.install_minutes is not None else None, p.labor_role) for p in products
    }


def _build_resolution_profiles(products: list[Product]) -> dict[int, float | None]:
    """product_id -> resolution_mp para `calculate_storage` (Motor 5)."""
    return {p.id: (float(p.resolution_mp) if p.resolution_mp is not None else None) for p in products}


def _build_storage_capacity_profiles(products: list[Product]) -> dict[int, float | None]:
    """product_id -> storage_capacity_gb para `calculate_storage` (Motor 5)."""
    return {p.id: (float(p.storage_capacity_gb) if p.storage_capacity_gb is not None else None) for p in products}


def _build_channel_capacity_profiles(products: list[Product]) -> dict[int, int | None]:
    """product_id -> channel_capacity para `calculate_capacity_warnings` (Motor 5)."""
    return {p.id: p.channel_capacity for p in products}


def _resolve_param(db: Session, key: str, overrides: dict[str, float]) -> float:
    """Valor de un `calculation_parameter` para esta generación: el override de Motor 4
    (`resolve_calculation_parameter_overrides`) si alguna `TechnicalRule` lo activó, si no
    el configurado/default de siempre."""
    if key in overrides:
        return overrides[key]
    return get_calculation_parameter(db, key)


def compute_survey_items(db: Session, context: str) -> tuple[list[dict], list[str], list[str]]:
    """Motor 1-5 sobre el expediente de un proyecto: interpreta, resuelve contra
    catálogo, aplica reglas (Motor 4) y las calculadoras de Motor 5. No persiste nada —
    la usan tanto la vista previa (`ai_budget_suggestions`) como el orquestador que sí
    persiste (`generate_documents_from_survey`).

    Devuelve `(items, warnings, engineering_notes)`: los ítems finales de presupuesto,
    las advertencias de capacidad (`CapacityCalculator`) y las notas de ingeniería que
    activaron las `TechnicalRule` de tipo `flag_engineering_note` presentes — esto
    último solo lo usa el orquestador, la vista previa lo descarta.
    """
    products = db.query(Product).order_by(Product.code).all()
    catalog = _build_catalog_dicts(products)
    technical_rules = db.query(TechnicalRule).all()
    rules = build_accessory_rule_dicts(db.query(CatalogRule).all(), technical_rules)
    product_prices = {p.id: float(p.price) for p in products}

    items = suggest_budget_items(context, catalog)
    items = expand_with_rules(items, catalog, rules)
    param_overrides = resolve_calculation_parameter_overrides(items, technical_rules)
    engineering_notes = resolve_engineering_notes(items, technical_rules)

    items = apply_cable_waste_margin(items, catalog, _resolve_param(db, CABLE_WASTE_MARGIN_KEY, param_overrides))
    items = calculate_storage(
        items,
        _build_resolution_profiles(products),
        _build_storage_capacity_profiles(products),
        _resolve_param(db, STORAGE_GB_PER_MP_PER_DAY_KEY, param_overrides),
        _resolve_param(db, STORAGE_RETENTION_DAYS_KEY, param_overrides),
    )
    labor_estimate = calculate_labor(
        items,
        _build_install_profiles(products),
        _resolve_param(db, LABOR_HOURLY_RATE_KEY, param_overrides),
        _resolve_param(db, LABOR_MAX_HOURS_PER_TECHNICIAN_KEY, param_overrides),
    )
    if labor_estimate is not None:
        items = items + [build_labor_budget_item(labor_estimate)]

    warnings = calculate_capacity_warnings(items, catalog, _build_channel_capacity_profiles(products))
    for item in items:
        if item.get("product_id") is not None:
            item["unit_price"] = product_prices.get(item["product_id"], 0)

    return items, warnings, engineering_notes


@dataclass
class DocumentSet:
    """Resultado de `generate_documents_from_survey`. `engineering_drafted` es la única
    señal de "ya existía" que aplica hoy: Budget/Quote siempre son una generación nueva
    (cada corrida es una foto del presupuesto a partir del estado actual del
    levantamiento, no hay concepto de "regenerar la misma" que idempotencia evitaría
    duplicar) — Engineering sí respeta lo que ya exista, por eso a ella sí le hace falta
    reportar si se rellenó o se dejó intacta."""

    budget: Budget
    quote: Quote
    engineering_drafted: bool
    warnings: list[str] = field(default_factory=list)


def generate_documents_from_survey(db: Session, project_id: int, context: str, created_by: int | None) -> DocumentSet:
    """Orquestador de Motor 6 — genera Presupuesto + Cotización (siempre) y un borrador
    de Ingeniería (best-effort, solo si el proyecto no tiene ingeniería propia todavía,
    para no pisar lo que oficina ya haya editado a mano). No comitea, no notifica — el
    caller (`api/routers/ai.py::generate_from_survey`) decide cuándo hacer ambas cosas,
    igual que ya hacían `build_budget`/`build_quote_from_budget` antes de esta función."""
    items, warnings, engineering_notes = compute_survey_items(db, context)
    if not items:
        raise HTTPException(status_code=400, detail="La IA no pudo derivar materiales del levantamiento")

    items_in = [BudgetItemIn(**item) for item in items]
    budget = build_budget(
        db, project_id, "Generado automáticamente desde el levantamiento", items_in, created_by, ai_generated=True
    )
    db.flush()  # build_quote_from_budget necesita budget.id
    quote = build_quote_from_budget(db, budget, created_by)

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
            observations = draft["observations"]
            if engineering_notes:
                # Motor 4 -> Motor 6: notas de flag_engineering_note activadas por
                # productos presentes en el presupuesto (ver resolve_engineering_notes).
                extra = "\n".join(engineering_notes)
                observations = f"{observations}\n{extra}" if observations else extra
            engineering.observations = observations
            engineering.ai_generated = True
            engineering_drafted = True
        except HTTPException as e:
            logger.warning("Borrador de ingeniería omitido para el proyecto %s: %s", project_id, e.detail)

    return DocumentSet(budget=budget, quote=quote, engineering_drafted=engineering_drafted, warnings=warnings)
