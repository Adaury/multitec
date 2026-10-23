"""Motor 2 — Catálogo inteligente (§ docs/ai-engine-architecture.md).

Resuelve las entidades detectadas por Motor 1 (`app.ai_engine.nlu`) contra productos
reales del catálogo, comparando nombre/categoría/tags/sinónimos. No interpreta lenguaje
natural — recibe entidades ya extraídas, nunca el texto crudo del levantamiento. Cuando el
modelo no logra resolver una entidad, `_apply_tag_fallback` recurre al matching
determinista de Motor 3 (`app.ai_engine.tagging.find_product_by_text`) antes de darla por
sin catálogo.
"""

import json
import logging
import re

from app.ai_engine.learning import LearnedMatches, phrase_matches
from app.ai_engine.nlu import interpret_survey_items
from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.ai_engine.tagging import find_product_by_text, normalize_text
from app.core.config import get_settings

logger = logging.getLogger("multitec.ai")


# Con un catálogo chico se le da completo al modelo (como siempre). Pasado ese tamaño el prompt ya
# no cabe en su contexto (4096 tokens): se trunca, pierde las instrucciones y genera sin parar. Por
# eso, con un catálogo grande solo se le pasan los productos que se parecen a lo detectado.
SMALL_CATALOG_LIMIT = 25
MAX_PROMPT_PRODUCTS = 40
MIN_CANDIDATES_PER_ENTITY = 3
MAX_CANDIDATES_PER_ENTITY = 6

_STOPWORDS = {
    "de", "del", "la", "las", "el", "los", "con", "para", "por", "un", "una", "unos", "unas", "y", "o",
    "en", "al", "a", "sin", "que", "se", "su", "sus", "x", "mas", "más",
}


def _tokens(text: str) -> set[str]:
    """Palabras normalizadas (sin tildes ni mayúsculas) y sin conectores; un plural simple (-s/-es)
    cuenta como la misma palabra (camaras == camara)."""
    out: set[str] = set()
    for word in re.findall(r"[a-z0-9]+", normalize_text(text)):
        if word in _STOPWORDS or len(word) < 2:
            continue
        out.add(word)
        if word.endswith("es") and len(word) > 4:
            out.add(word[:-2])
        elif word.endswith("s") and len(word) > 3:
            out.add(word[:-1])
    return out


def _candidate_score(entity_text: str, product: dict) -> int:
    """Qué tan parecido es un producto a lo detectado: coincidencia con sinónimos (lo más fuerte,
    son cómo la empresa llama al producto), nombre, etiquetas y categoría."""
    entity = normalize_text(entity_text)
    words = _tokens(entity_text)
    if not words:
        return 0
    score = 0
    for synonym in product.get("synonyms") or []:
        phrase = normalize_text(synonym)
        if phrase and re.search(rf"\b{re.escape(phrase)}\b", entity):
            score += 6
    score += 3 * len(words & _tokens(product["name"]))
    for tag in product.get("tags") or []:
        score += 2 * len(words & _tokens(tag))
    score += len(words & _tokens(str(product.get("category") or "")))

    # Los números distinguen modelos casi iguales ("Switch PoE 16 puertos" vs "8 puertos" vs "24"):
    # coincidir en el número suma mucho y contradecirlo resta, para que el modelo correcto gane
    # con ventaja clara en vez de quedar empatado y depender de la IA.
    wanted = set(re.findall(r"\d+(?:\.\d+)?", entity))
    have = set(re.findall(r"\d+(?:\.\d+)?", normalize_text(product["name"])))
    if wanted and have:
        score += 5 if wanted & have else -4
    return score


def shortlist_catalog(entities: list[dict], catalog: list[dict]) -> list[dict]:
    """Productos que van al prompt: todo el catálogo si es chico; si no, los más parecidos a cada
    entidad detectada (con un tope total para que el prompt siempre quepa)."""
    if len(catalog) <= SMALL_CATALOG_LIMIT:
        return catalog

    per_entity = max(
        MIN_CANDIDATES_PER_ENTITY,
        min(MAX_CANDIDATES_PER_ENTITY, MAX_PROMPT_PRODUCTS // max(1, len(entities))),
    )
    best: dict[int, int] = {}
    for entity in entities:
        scored = sorted(
            ((_candidate_score(entity["description"], p), p["id"]) for p in catalog),
            key=lambda sp: (-sp[0], sp[1]),
        )
        for score, product_id in scored[:per_entity]:
            if score > 0:
                best[product_id] = max(best.get(product_id, 0), score)

    chosen = sorted(best, key=lambda pid: (-best[pid], pid))[:MAX_PROMPT_PRODUCTS]
    if not chosen:
        # Nada se parece (descripciones raras): mejor un recorte del catálogo que ninguno.
        return catalog[:MAX_PROMPT_PRODUCTS]
    keep = set(chosen)
    return [p for p in catalog if p["id"] in keep]


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


def _apply_tag_fallback(items: list[dict], catalog: list[dict]) -> list[dict]:
    """Motor 3, filtro determinista de respaldo: para las entidades que el modelo no
    logró resolver (`product_id=None`), intenta un último match por texto/tags/sinónimos
    (`app.ai_engine.tagging.find_product_by_text`) antes de darlas por perdidas. Nunca
    pisa un match que el modelo sí encontró — es un respaldo, no una segunda opinión."""
    result = []
    for item in items:
        if item.get("product_id") is None:
            fallback_id = find_product_by_text(item["description"], catalog)
            if fallback_id is not None:
                item = {**item, "product_id": fallback_id}
        result.append(item)
    return result


def _apply_learned_overrides(items: list[dict], learned: LearnedMatches | None, catalog: list[dict]) -> list[dict]:
    """Motor 7 -> Motor 2: una frase que los humanos corrigieron al mismo producto varias veces
    (ver `learning.get_learned_matches`) se resuelve directo a ese producto, por encima de lo que
    haya decidido el modelo. Gana la frase más larga (la más específica); un producto que ya no
    está en el catálogo se ignora."""
    if not learned or not learned.overrides:
        return items
    catalog_ids = {p["id"] for p in catalog}
    result = []
    for item in items:
        matches = [
            (phrase, product_id)
            for phrase, product_id in learned.overrides.items()
            if product_id in catalog_ids and phrase_matches(item["description"], phrase)
        ]
        if matches:
            _, product_id = max(matches, key=lambda m: len(m[0]))
            item = {**item, "product_id": product_id}
        result.append(item)
    return result


def _format_learned_hints(entities: list[dict], learned: LearnedMatches | None, catalog: list[dict]) -> str:
    """Pistas para el prompt: correcciones sueltas (aún no confirmadas) cuyas palabras aparecen en
    lo detectado. Le dicen al modelo cómo la empresa llama a sus productos sin imponérselo."""
    if not learned or not learned.hints:
        return ""
    names = {p["id"]: p["name"] for p in catalog}
    words = {w for e in entities for w in normalize_text(e["description"]).split() if len(w) >= 4}
    lines = [
        f'- "{phrase}" → id={product_id}: {names[product_id]}'
        for phrase, product_id in learned.hints
        if product_id in names and words & set(phrase.split())
    ]
    if not lines:
        return ""
    return (
        "Correcciones anteriores de esta empresa (cómo llaman sus técnicos a sus productos; "
        "úsalas cuando apliquen):\n" + "\n".join(lines) + "\n\n"
    )


# Con un catálogo grande, primero se empareja por texto (rápido y sin IA) y la IA solo decide lo que
# de verdad es ambiguo. En esta máquina el modelo genera ~2-3 tokens/s: preguntarle por cada elemento
# costaba más de 3 minutos, y casi siempre el mejor candidato por texto ya era el correcto.
CONFIDENT_SCORE = 10
CONFIDENT_MARGIN = 3

COMPACT_MATCH_SCHEMA = {
    "type": "object",
    "properties": {"product_ids": {"type": "array", "items": {"type": "integer"}}},
    "required": ["product_ids"],
}


def resolve_confident_matches(entities: list[dict], catalog: list[dict]) -> tuple[dict[int, int], list[int]]:
    """Devuelve ({índice: product_id} de lo que el texto resuelve con claridad, [índices ambiguos]).
    Claro = el mejor producto puntúa alto Y le saca ventaja al segundo (si dos productos casi
    empatan —p. ej. dos modelos de cámara— es una decisión para la IA, no para el texto)."""
    resolved: dict[int, int] = {}
    ambiguous: list[int] = []
    for index, entity in enumerate(entities):
        ranked = sorted(
            ((_candidate_score(entity["description"], p), p["id"]) for p in catalog),
            key=lambda sp: (-sp[0], sp[1]),
        )
        best_score, best_id = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else 0
        if best_score <= 0:
            # No se parece a nada del catálogo (mano de obra, un servicio, algo que no se vende):
            # preguntarle a la IA solo la empuja a inventar un producto. Queda sin producto.
            continue
        if best_score >= CONFIDENT_SCORE and best_score - runner_up >= CONFIDENT_MARGIN:
            resolved[index] = best_id
        else:
            ambiguous.append(index)
    return resolved, ambiguous


def _match_ambiguous_with_model(
    entities: list[dict], catalog: list[dict], learned: LearnedMatches | None
) -> dict[int, int]:
    """Pregunta al modelo solo por las entidades ambiguas, con candidatos acotados y una respuesta
    compacta (un entero por elemento). Si el modelo falla, devuelve {}: esas entidades quedan sin
    producto para el respaldo determinista, en vez de tumbar toda la cotización."""
    if not entities:
        return {}
    settings = get_settings()
    client = get_client()
    candidates = shortlist_catalog(entities, catalog)
    catalog_text = "\n".join(_format_catalog_line(p) for p in candidates)
    entities_text = "\n".join(f"{i}: {e['quantity']} x {e['description']}" for i, e in enumerate(entities))
    prompt = (
        "Eres un especialista en catálogo de seguridad electrónica. Para cada elemento de la lista, "
        "elige el product_id del catálogo que le corresponde (compara nombre, categoría, etiquetas y "
        "sinónimos). Si ninguno corresponde (mano de obra, servicios), usa 0.\n\n"
        f"Devuelve un objeto JSON compacto {{\"product_ids\": [...]}} con EXACTAMENTE {len(entities)} "
        "enteros, uno por elemento y en el mismo orden.\n\n"
        f"{_format_learned_hints(entities, learned, catalog)}"
        f"Catálogo disponible:\n{catalog_text}\n\n"
        f"Elementos:\n{entities_text}"
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=COMPACT_MATCH_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options={**OLLAMA_OPTIONS, "temperature": 0, "num_predict": 40 + 8 * len(entities)},
        )
        return json.loads(response.message.content)["product_ids"]

    try:
        ids = _call(run)
    except Exception:
        logger.warning("Emparejamiento con IA omitido: se usan solo las coincidencias por texto")
        return {}
    valid = {p["id"] for p in catalog}
    return {i: pid for i, pid in enumerate(ids[: len(entities)]) if pid in valid}


def match_entities_to_catalog(
    entities: list[dict], catalog: list[dict], learned: LearnedMatches | None = None
) -> list[dict]:
    """Por cada entidad detectada por Motor 1, decide a qué producto del catálogo
    corresponde (o ninguno, ej. mano de obra o servicios). El modelo solo devuelve el
    `product_id` por índice — nunca vuelve a generar descripción ni cantidad, para no
    arriesgar que las altere en un segundo paso."""
    if not entities:
        return []

    return _match_text_first(entities, catalog, learned)


def _prefer_text_over_contradicting_model(description: str, model_choice: int, catalog: list[dict]) -> int:
    """El modelo local (3B) a veces elige un producto que el texto contradice (ej. "cable UTP de 200
    metros" -> conector RJ45). Si el producto elegido no coincide en nada con lo detectado
    (puntaje <= 0) pero otro sí (puntaje > 0), gana el de texto; si no, se respeta al modelo."""
    scored = sorted(((_candidate_score(description, p), p["id"]) for p in catalog), key=lambda sp: (-sp[0], sp[1]))
    best_score, best_id = scored[0]
    chosen_score = next((score for score, pid in scored if pid == model_choice), 0)
    return best_id if best_score > 0 and chosen_score <= 0 else model_choice


def _match_text_first(
    entities: list[dict], catalog: list[dict], learned: LearnedMatches | None
) -> list[dict]:
    """Texto primero, IA solo para lo ambiguo (ver resolve_confident_matches). Se usa con cualquier
    tamaño de catálogo: darle todo el catálogo al modelo local lo hacía confundir productos parecidos
    (conectores vs. cable) y, a veces, generar sin parar hasta cortar el JSON."""
    resolved, ambiguous = resolve_confident_matches(entities, catalog)
    if ambiguous:
        sub_entities = [entities[i] for i in ambiguous]
        for sub_index, product_id in _match_ambiguous_with_model(sub_entities, catalog, learned).items():
            if product_id:  # 0 = "ninguno"
                resolved[ambiguous[sub_index]] = _prefer_text_over_contradicting_model(
                    sub_entities[sub_index]["description"], product_id, catalog
                )
    matches = [{"index": i, "product_id": pid} for i, pid in resolved.items()]
    items = _merge_entities_with_matches(entities, matches)
    items = _apply_tag_fallback(items, catalog)
    return _apply_learned_overrides(items, learned, catalog)


def suggest_budget_items(
    project_context: str, catalog: list[dict], learned: LearnedMatches | None = None
) -> list[dict]:
    """Pipeline Motor 1 → Motor 2: interpreta el expediente en entidades y las resuelve
    contra el catálogo. Dos llamadas al modelo en vez de una — la interpretación no ve el
    catálogo y el matching no reinterpreta el texto — para poder conservar una entidad
    detectada aunque no tenga producto de catálogo, y para poder reusar la interpretación
    en otras áreas técnicas sin acoplarla a este catálogo en particular."""
    entities = interpret_survey_items(project_context)
    return match_entities_to_catalog(entities, catalog, learned)
