"""Motor 7 — Aprendizaje (§ docs/ai-engine-architecture.md).

Captura pasiva únicamente: registra qué corrigió un humano sobre un `Budget` o una
`Engineering` que la IA generó, sin cambiar el flujo de trabajo de quien edita. No agrega
patrones, no reescribe `CatalogRule` ni `Product.tags`, no genera propuestas — ese
análisis periódico queda para cuando haya volumen suficiente de proyectos (ver el plan de
evolución del documento de arquitectura). Aquí solo se escribe la señal cruda.
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai_engine.tagging import normalize_text
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
from app.models.product import Product
from app.models.product_match_correction import ProductMatchCorrection
from app.models.voice_survey_example import VoiceSurveyExample

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
    db: Session,
    project_id: int,
    budget: Budget,
    new_items: list[tuple[int | None, str, float]],
    user_id: int | None = None,
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
                    budget_id=budget.id,
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
                    budget_id=budget.id,
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
                    budget_id=budget.id,
                    entity_type=ENTITY_TYPE_BUDGET_ITEM,
                    origin=ORIGIN_HUMAN_MODIFIED,
                    product_id=product_id,
                    field_changed="quantity",
                    old_value=str(old_quantity),
                    new_value=str(new_quantity),
                )
            )

    _record_product_replacements(db, project_id, budget, new_items, user_id)
    budget.ai_generated = False


def _pair_replacements(removed: list[tuple], added: list[tuple]) -> list[tuple[tuple, tuple]]:
    """Empareja una línea quitada con una agregada solo cuando es inequívoco: misma cantidad y
    ninguna otra candidata de ese lado ni del otro. Una sustitución de producto no deja rastro
    explícito (la edición manda la lista final), así que se infiere — con dudas, no se aprende."""
    pairs = []
    for r in removed:
        candidates = [a for a in added if a[2] == r[2]]
        if len(candidates) != 1:
            continue
        a = candidates[0]
        if sum(1 for x in removed if x[2] == a[2]) != 1:
            continue
        pairs.append((r, a))
    return pairs


def _record_product_replacements(
    db: Session,
    project_id: int,
    budget: Budget,
    new_items: list[tuple[int | None, str, float]],
    user_id: int | None,
) -> None:
    """Aprendizaje de sinónimos: si el humano quitó una línea (lo que la IA emparejó mal, o no
    emparejó) y puso otro producto en su lugar, queda registrado "dijo X → es el producto Y".
    Solo cuenta la descripción que dijo el técnico: las líneas cuya descripción es el nombre del
    propio producto (accesorios agregados por reglas) no son algo que alguien dijera."""
    new_keys = {_budget_item_key(pid, desc) for pid, desc, _ in new_items}
    old_keys = {_budget_item_key(i.product_id, i.description) for i in budget.items}

    removed = [
        (i.product_id, i.description, float(i.quantity))
        for i in budget.items
        if _budget_item_key(i.product_id, i.description) not in new_keys
    ]
    added = [
        (pid, desc, float(q))
        for pid, desc, q in new_items
        if pid is not None and _budget_item_key(pid, desc) not in old_keys
    ]
    if not removed or not added:
        return

    removed_ids = {r[0] for r in removed if r[0] is not None}
    names = (
        {pid: normalize_text(name) for pid, name in db.query(Product.id, Product.name).filter(Product.id.in_(removed_ids))}
        if removed_ids
        else {}
    )
    spoken = [r for r in removed if normalize_text(r[1]) and normalize_text(r[1]) != names.get(r[0])]

    for removed_line, added_line in _pair_replacements(spoken, added):
        db.add(
            ProductMatchCorrection(
                project_id=project_id,
                budget_id=budget.id,
                spoken_text=removed_line[1].strip()[:255],
                ai_product_id=removed_line[0],
                human_product_id=added_line[0],
                created_by=user_id,
            )
        )


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


# --- Levantamiento por voz: aprender cómo la empresa reparte lo dictado -----------------------

VOICE_FIELDS = ("notes", "measurements", "observations")
# El modelo local tiene poco contexto: pocos ejemplos y cortos. Se prefieren las correcciones
# (lo que la IA hizo mal) sobre los aciertos.
VOICE_EXAMPLES_LIMIT = 3
VOICE_EXAMPLE_MAX_CHARS = 700


def record_voice_feedback(
    db: Session,
    project_id: int,
    transcript: str,
    ai_fields: dict[str, str],
    final_fields: dict[str, str],
    ai_classified: bool,
    created_by: int | None,
) -> VoiceSurveyExample:
    """Guarda lo que dijo el técnico, cómo lo repartió la IA y cómo lo dejó él al revisarlo.
    `corrected` es True si el técnico cambió cualquier campo (ignorando espacios al borde)."""
    ai = {f: (ai_fields.get(f) or "").strip() for f in VOICE_FIELDS}
    final = {f: (final_fields.get(f) or "").strip() for f in VOICE_FIELDS}
    example = VoiceSurveyExample(
        project_id=project_id,
        transcript=transcript.strip(),
        ai_notes=ai["notes"],
        ai_measurements=ai["measurements"],
        ai_observations=ai["observations"],
        final_notes=final["notes"],
        final_measurements=final["measurements"],
        final_observations=final["observations"],
        ai_classified=ai_classified,
        corrected=ai != final,
        created_by=created_by,
    )
    db.add(example)
    return example


def recent_voice_examples(db: Session, limit: int = VOICE_EXAMPLES_LIMIT) -> list[dict]:
    """Ejemplos para el prompt del reparto: primero las correcciones más recientes y, si no
    alcanzan, los aciertos más recientes. Devuelve `{transcript, notes, measurements,
    observations}` con lo que dejó el técnico (la versión buena), sin dictados vacíos ni largos."""
    rows = (
        db.query(VoiceSurveyExample)
        .filter(func.length(VoiceSurveyExample.transcript) <= VOICE_EXAMPLE_MAX_CHARS)
        .filter(
            (VoiceSurveyExample.final_notes != "")
            | (VoiceSurveyExample.final_measurements != "")
            | (VoiceSurveyExample.final_observations != "")
        )
        .order_by(VoiceSurveyExample.corrected.desc(), VoiceSurveyExample.created_at.desc(), VoiceSurveyExample.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "transcript": r.transcript,
            "notes": r.final_notes,
            "measurements": r.final_measurements,
            "observations": r.final_observations,
        }
        for r in rows
    ]


# --- Sinónimos de producto: aprender cómo dicen los técnicos lo que hay en el catálogo --------

# Con una sola corrección puede ser un error o un caso raro: solo se le da la razón a los
# humanos sobre el modelo cuando la misma frase se corrigió al mismo producto 2+ veces y sin
# que otro producto le haya ganado.
MIN_CONFIRMATIONS = 2
HINTS_LIMIT = 8


@dataclass
class LearnedMatches:
    """`overrides`: frase normalizada -> producto confirmado (reemplaza lo que decida el modelo).
    `hints`: correcciones sueltas recientes (frase normalizada, producto) que solo se le muestran
    al modelo como pista, sin imponerlas."""

    overrides: dict[str, int] = field(default_factory=dict)
    hints: list[tuple[str, int]] = field(default_factory=list)


def get_learned_matches(db: Session) -> LearnedMatches:
    rows = (
        db.query(ProductMatchCorrection)
        .order_by(ProductMatchCorrection.created_at.desc(), ProductMatchCorrection.id.desc())
        .limit(500)
        .all()
    )
    counts: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        phrase = normalize_text(row.spoken_text)
        if phrase:
            counts[phrase][row.human_product_id] += 1

    learned = LearnedMatches()
    for phrase, counter in counts.items():
        ranked = counter.most_common()
        top_id, top_count = ranked[0]
        if top_count >= MIN_CONFIRMATIONS and (len(ranked) == 1 or top_count > ranked[1][1]):
            learned.overrides[phrase] = top_id

    seen: set[tuple[str, int]] = set()
    for row in rows:  # más recientes primero
        phrase = normalize_text(row.spoken_text)
        key = (phrase, row.human_product_id)
        if not phrase or phrase in learned.overrides or key in seen:
            continue
        seen.add(key)
        learned.hints.append(key)
        if len(learned.hints) >= HINTS_LIMIT:
            break
    return learned


def phrase_matches(description: str, phrase: str) -> bool:
    """¿`description` es la frase aprendida o la contiene como palabra(s) completa(s)?"""
    normalized = normalize_text(description)
    return normalized == phrase or bool(re.search(rf"\b{re.escape(phrase)}\b", normalized))
