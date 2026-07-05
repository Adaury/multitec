"""Motor 7 — Aprendizaje (§ docs/ai-engine-architecture.md).

Captura pasiva únicamente: registra qué corrigió un humano sobre un `Budget` o una
`Engineering` que la IA generó, sin cambiar el flujo de trabajo de quien edita. No agrega
patrones, no reescribe `CatalogRule` ni `Product.tags`, no genera propuestas — ese
análisis periódico queda para cuando haya volumen suficiente de proyectos (ver el plan de
evolución del documento de arquitectura). Aquí solo se escribe la señal cruda.
"""

from sqlalchemy.orm import Session

from app.models.ai_feedback_event import (
    ENTITY_TYPE_BUDGET_ITEM,
    ENTITY_TYPE_ENGINEERING,
    ORIGIN_HUMAN_ADDED,
    ORIGIN_HUMAN_MODIFIED,
    ORIGIN_HUMAN_REMOVED,
    AIFeedbackEvent,
)
from app.models.budget import Budget
from app.models.engineering import Engineering

ENGINEERING_FIELDS = (
    "recommended_equipment",
    "distribution",
    "conduits",
    "wiring",
    "technical_design",
    "observations",
)


def _budget_item_key(product_id: int | None, description: str):
    """Clave de emparejamiento entre la versión de la IA y la editada. Con product_id
    (el caso normal) empareja por producto; sin él (mano de obra/servicios sueltos)
    empareja por descripción — no es a prueba de líneas duplicadas idénticas, pero esto
    es una señal de aprendizaje best-effort, no un cálculo financiero."""
    return product_id if product_id is not None else ("desc", description)


def record_budget_edit_feedback(
    db: Session, project_id: int, budget: Budget, new_items: list[tuple[int | None, str, float]]
) -> None:
    """Si `budget.ai_generated` sigue en True, compara sus líneas actuales (= lo que
    sugirió la IA, porque nada las tocó todavía) contra `new_items` (lo que un humano está
    a punto de dejar) y registra un `AIFeedbackEvent` por cada línea agregada, quitada o
    con cantidad distinta. Debe llamarse ANTES de aplicar el cambio (mientras `budget.items`
    todavía tiene el contenido original). Pone `ai_generated=False` al final — la próxima
    edición ya no tiene una "sugerencia de IA" original con la cual contrastar."""
    if not budget.ai_generated:
        return

    old_by_key = {
        _budget_item_key(item.product_id, item.description): (item.product_id, float(item.quantity))
        for item in budget.items
    }
    new_by_key = {
        _budget_item_key(product_id, description): (product_id, float(quantity))
        for product_id, description, quantity in new_items
    }

    for key, (product_id, old_quantity) in old_by_key.items():
        if key not in new_by_key:
            db.add(
                AIFeedbackEvent(
                    project_id=project_id,
                    entity_type=ENTITY_TYPE_BUDGET_ITEM,
                    origin=ORIGIN_HUMAN_REMOVED,
                    product_id=product_id,
                    old_value=str(old_quantity),
                )
            )

    for key, (product_id, new_quantity) in new_by_key.items():
        if key not in old_by_key:
            db.add(
                AIFeedbackEvent(
                    project_id=project_id,
                    entity_type=ENTITY_TYPE_BUDGET_ITEM,
                    origin=ORIGIN_HUMAN_ADDED,
                    product_id=product_id,
                    new_value=str(new_quantity),
                )
            )
            continue
        old_product_id, old_quantity = old_by_key[key]
        if old_quantity != new_quantity:
            db.add(
                AIFeedbackEvent(
                    project_id=project_id,
                    entity_type=ENTITY_TYPE_BUDGET_ITEM,
                    origin=ORIGIN_HUMAN_MODIFIED,
                    product_id=product_id,
                    field_changed="quantity",
                    old_value=str(old_quantity),
                    new_value=str(new_quantity),
                )
            )

    budget.ai_generated = False


def record_engineering_edit_feedback(db: Session, project_id: int, engineering: Engineering, new_values: dict) -> None:
    """Igual que `record_budget_edit_feedback` pero para los campos de texto de
    `Engineering`. `new_values` son los campos presentes en el payload (solo los que el
    caller va a aplicar) — un campo ausente no se compara. Debe llamarse ANTES de aplicar
    `new_values` sobre `engineering`."""
    if not engineering.ai_generated:
        return

    for field, new_value in new_values.items():
        if field not in ENGINEERING_FIELDS:
            continue
        old_value = getattr(engineering, field)
        if old_value != new_value:
            db.add(
                AIFeedbackEvent(
                    project_id=project_id,
                    entity_type=ENTITY_TYPE_ENGINEERING,
                    origin=ORIGIN_HUMAN_MODIFIED,
                    field_changed=field,
                    old_value=old_value,
                    new_value=new_value,
                )
            )

    engineering.ai_generated = False
