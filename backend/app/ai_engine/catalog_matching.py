"""Motor 2 — Catálogo inteligente (§ docs/ai-engine-architecture.md).

Resuelve las entidades detectadas por Motor 1 (`app.ai_engine.nlu`) contra productos
reales del catálogo, comparando nombre/categoría/tags/sinónimos. No interpreta lenguaje
natural — recibe entidades ya extraídas, nunca el texto crudo del levantamiento.
"""

import json

from app.ai_engine.nlu import interpret_survey_items
from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.core.config import get_settings


def _format_catalog_line(p: dict) -> str:
    """Una línea de catálogo con contexto semántico — nombre, categoría, unidad, y
    tags/sinónimos para el matching. Los accesorios relacionados (NVR por cámara, RJ45 por
    cable, etc.) NO se le piden a la IA — se resuelven aparte, de forma determinista y con
    cantidad exacta, en `app.ai_engine.rules.expand_with_rules` (el modelo local no es
    confiable para esa aritmética)."""
    parts = [f"- id={p['id']}: {p['name']} (categoría: {p['category']}, unidad: {p.get('unit', 'unidad')})"]
    if p.get("tags"):
        parts.append(f"  etiquetas: {', '.join(p['tags'])}")
    if p.get("synonyms"):
        parts.append(f"  sinónimos: {', '.join(p['synonyms'])}")
    return "\n".join(parts)


CATALOG_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "product_id": {"type": "integer"},
                },
                "required": ["index", "product_id"],
            },
        }
    },
    "required": ["matches"],
}


def _merge_entities_with_matches(entities: list[dict], matches: list[dict]) -> list[dict]:
    """Combina las entidades detectadas por Motor 1 (fuente de verdad para descripción y
    cantidad) con el resultado del matching de Motor 2 (que solo decide el product_id) por
    índice. Un índice que el modelo no devuelva se trata como sin match, no como error —
    la entidad se conserva igual (con product_id=None) en vez de desaparecer."""
    product_id_by_index = {m["index"]: m.get("product_id") for m in matches}
    items = []
    for i, entity in enumerate(entities):
        product_id = product_id_by_index.get(i) or None  # 0 (o ausente) = sin match en catálogo
        items.append(
            {
                "product_id": product_id,
                "description": entity["description"],
                "quantity": entity["quantity"],
            }
        )
    return items


def match_entities_to_catalog(entities: list[dict], catalog: list[dict]) -> list[dict]:
    """Por cada entidad detectada por Motor 1, decide a qué producto del catálogo
    corresponde (o ninguno, ej. mano de obra o servicios). El modelo solo devuelve el
    `product_id` por índice — nunca vuelve a generar descripción ni cantidad, para no
    arriesgar que las altere en un segundo paso."""
    if not entities:
        return []

    settings = get_settings()
    client = get_client()

    catalog_text = "\n".join(_format_catalog_line(p) for p in catalog)
    entities_text = "\n".join(f"{i}: {e['quantity']} x {e['description']}" for i, e in enumerate(entities))
    prompt = (
        "Eres un especialista en catálogo de seguridad electrónica. A continuación hay una "
        "lista de materiales o servicios detectados en un levantamiento (cada uno con un "
        "índice) y el catálogo disponible.\n\n"
        "Para cada elemento de la lista, identifica a qué producto del catálogo "
        "corresponde comparando contra su nombre, categoría, etiquetas y sinónimos — no "
        "solo el nombre exacto (ej. \"domo\" o \"cctv\" pueden referirse a una cámara "
        "aunque no diga \"cámara\" textualmente). Si el elemento no corresponde a ningún "
        "producto del catálogo (por ejemplo, mano de obra o un servicio), usa product_id 0.\n\n"
        "Devuelve, para CADA índice de la lista, su product_id correspondiente — no omitas "
        "ninguno.\n\n"
        f"Catálogo disponible:\n{catalog_text}\n\n"
        f"Elementos detectados:\n{entities_text}"
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=CATALOG_MATCH_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options=OLLAMA_OPTIONS,
        )
        return json.loads(response.message.content)["matches"]

    matches = _call(run)
    return _merge_entities_with_matches(entities, matches)


def suggest_budget_items(project_context: str, catalog: list[dict]) -> list[dict]:
    """Pipeline Motor 1 → Motor 2: interpreta el expediente en entidades y las resuelve
    contra el catálogo. Dos llamadas al modelo en vez de una — la interpretación no ve el
    catálogo y el matching no reinterpreta el texto — para poder conservar una entidad
    detectada aunque no tenga producto de catálogo, y para poder reusar la interpretación
    en otras áreas técnicas sin acoplarla a este catálogo en particular."""
    entities = interpret_survey_items(project_context)
    return match_entities_to_catalog(entities, catalog)
