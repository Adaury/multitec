"""Motor 3 — Sistema de etiquetas (§ docs/ai-engine-architecture.md).

Centraliza la normalización de texto en español y el matching por nombre/tags/sinónimos
que antes vivía disperso (hardcodeado dentro del prompt de Motor 2, en
`catalog_matching._format_catalog_line`). No es una tabla nueva — sigue leyendo
`Product.tags`/`Product.synonyms` (JSON) tal como están; esto es la capa de comparación
reusable que faltaba, no un cambio de almacenamiento.

Motor 2 lo usa como filtro determinista de respaldo: cuando el modelo local no logra
resolver una entidad contra el catálogo (`product_id=None`), `find_product_by_text`
intenta un último match por substring normalizado antes de darla por perdida. No
reemplaza el matching semántico del modelo (que entiende sinónimos no declarados, ej.
"domo" → cámara, sin que el catálogo tenga ese tag) — es solo un respaldo para no perder
un match obvio por texto casi exacto cuando el modelo falla.
"""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """minúsculas, sin tildes/diacríticos, espacios colapsados — para comparar
    tags/sinónimos/descripciones de forma consistente sin importar cómo los haya escrito
    quien cargó el producto o quien describió el levantamiento."""
    text = text.strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text)


def _product_search_terms(product: dict) -> set[str]:
    """Todos los términos normalizados por los que se puede reconocer un producto: su
    nombre, sus tags y sus sinónimos."""
    terms = {normalize_text(product["name"])}
    terms.update(normalize_text(t) for t in product.get("tags") or [])
    terms.update(normalize_text(s) for s in product.get("synonyms") or [])
    return {t for t in terms if t}


def find_product_by_text(description: str, catalog: list[dict]) -> int | None:
    """Busca, por substring de palabra completa normalizado, si `description` menciona el
    nombre/tag/sinónimo de algún producto del catálogo. Devuelve el primer producto que
    matchea, en el orden recibido (el caller ordena por código, igual que
    `expand_with_rules`) — `None` si ninguno coincide.

    Coincidencia de palabra completa, con plural simple (-s/-es) tolerado (ej. tag
    "camara" matchea "cámaras" en la descripción) — para evitar falsos positivos obvios
    como que el tag "cable" matchee dentro de "cableado eléctrico" (dos cosas distintas
    que comparten una raíz de texto, pero "cableado" no es el plural de "cable"). No
    intenta stemming completo del español, solo esta forma común."""
    normalized_description = normalize_text(description)
    if not normalized_description:
        return None

    for product in catalog:
        for term in _product_search_terms(product):
            if re.search(rf"\b{re.escape(term)}(?:s|es)?\b", normalized_description):
                return product["id"]
    return None
