"""Motor 4 — Motor de reglas técnicas (§ docs/ai-engine-architecture.md).

Dos fuentes de reglas conviven aquí a propósito: `CatalogRule` (el modelo original, un
solo tipo de acción, sin migrar) y `TechnicalRule` (la generalización hacia adelante,
condición/acción tipada). `TechnicalRule` ya implementa sus tres tipos de acción:
`add_accessory` (`build_accessory_rule_dicts`, unido con `CatalogRule`),
`set_calculation_parameter` (`resolve_calculation_parameter_overrides`, hacia Motor 5) y
`flag_engineering_note` (`resolve_engineering_notes`, hacia Motor 6).
"""

import math

from app.models.catalog_rule import CatalogRule
from app.models.technical_rule import (
    ACTION_TYPE_ADD_ACCESSORY,
    ACTION_TYPE_FLAG_ENGINEERING_NOTE,
    ACTION_TYPE_SET_CALCULATION_PARAMETER,
    TechnicalRule,
)


def expand_with_rules(items: list[dict], catalog: list[dict], rules: list[dict]) -> list[dict]:
    """Post-procesamiento determinista (sin IA) para la generación automática de
    presupuesto desde el levantamiento (§ catálogo inteligente v2).

    La IA (modelo local, modesto) hace bien el matching semántico de lo que el técnico dijo
    explícitamente, pero no es confiable para reglas de cantidad tipo "1 disco duro por cada
    4 cámaras" — así que esa aritmética se resuelve aquí con datos del catálogo (CatalogRule),
    no con el modelo.

    `rules` es una lista de dicts (source_product_id, target_tag, per_source_units,
    quantity) — una fila por regla, ya cargadas de la tabla `catalog_rules`. Por cada ítem ya
    sugerido con product_id, se buscan sus reglas; el accesorio objetivo es el primer
    producto del catálogo (en el orden recibido — el caller lo ordena por código) cuyo `tags`
    contenga `target_tag`. Modo fijo (`per_source_units` nulo): agrega `quantity` una sola
    vez. Modo proporcional: `lotes = ceil(cantidad_fuente / per_source_units)`, agrega
    `quantity * lotes`. Si varias reglas apuntan al mismo accesorio, las cantidades se suman.
    Un accesorio que el técnico ya mencionó explícitamente no se toca.
    """
    included_ids = {item["product_id"] for item in items if item.get("product_id")}

    rules_by_source: dict[int, list[dict]] = {}
    for rule in rules:
        rules_by_source.setdefault(rule["source_product_id"], []).append(rule)

    added_quantity: dict[int, float] = {}
    added_names: dict[int, str] = {}

    for item in items:
        product_id = item.get("product_id")
        if not product_id or product_id not in rules_by_source:
            continue
        source_qty = item.get("quantity") or 0

        for rule in rules_by_source[product_id]:
            target = next((c for c in catalog if rule["target_tag"] in (c.get("tags") or [])), None)
            if target is None or target["id"] in included_ids:
                continue

            per_source_units = rule.get("per_source_units")
            if per_source_units:
                if source_qty <= 0:
                    continue
                lots = math.ceil(source_qty / per_source_units)
                qty_to_add = lots * rule["quantity"]
            else:
                qty_to_add = rule["quantity"]

            added_quantity[target["id"]] = added_quantity.get(target["id"], 0) + qty_to_add
            added_names[target["id"]] = target["name"]

    extra_items = [
        {"product_id": product_id, "description": added_names[product_id], "quantity": qty}
        for product_id, qty in added_quantity.items()
    ]
    return items + extra_items


def _catalog_rule_to_dict(rule: CatalogRule) -> dict:
    return {
        "source_product_id": rule.source_product_id,
        "target_tag": rule.target_tag,
        "per_source_units": float(rule.per_source_units) if rule.per_source_units is not None else None,
        "quantity": float(rule.quantity),
    }


def _technical_rule_to_dict(rule: TechnicalRule) -> dict | None:
    """None si el action_type de la regla no tiene manejador todavía — hoy solo
    add_accessory lo tiene. Cuando se registre un manejador nuevo (Motor 5/6), este es el
    punto donde se agrega su propia conversión."""
    if rule.action_type != ACTION_TYPE_ADD_ACCESSORY:
        return None
    return {
        "source_product_id": rule.source_product_id,
        "target_tag": rule.target_tag,
        "per_source_units": rule.per_source_units,
        "quantity": rule.quantity,
    }


def build_accessory_rule_dicts(catalog_rules: list[CatalogRule], technical_rules: list[TechnicalRule]) -> list[dict]:
    """Combina `CatalogRule` (todas) y `TechnicalRule` (solo las de action_type
    'add_accessory') en la lista de dicts que espera `expand_with_rules` — el punto de
    unión entre el mecanismo de reglas original y su generalización."""
    dicts = [_catalog_rule_to_dict(r) for r in catalog_rules]
    dicts.extend(d for r in technical_rules if (d := _technical_rule_to_dict(r)) is not None)
    return dicts


def _present_product_ids(items: list[dict]) -> set[int]:
    return {item["product_id"] for item in items if item.get("product_id")}


def resolve_calculation_parameter_overrides(items: list[dict], technical_rules: list[TechnicalRule]) -> dict[str, float]:
    """Motor 4 → Motor 5: por cada `TechnicalRule` de tipo `set_calculation_parameter`
    cuyo `source_product_id` está presente en `items` (ítems ya resueltos del
    presupuesto), devuelve el valor a usar para ese `parameter_key` en vez del default
    de `calculation_parameters` — solo para esta generación, no se persiste.

    Si varias reglas activas apuntan a la misma clave (ej. dos productos distintos que
    ambos suben el margen de desperdicio de cable), se usa el valor más alto: todas las
    reglas de este tipo hoy suben un parámetro para un caso especial, nunca lo bajan, así
    que el valor más conservador es el más alto, no el último que se evalúe."""
    present_ids = _present_product_ids(items)
    overrides: dict[str, float] = {}
    for rule in technical_rules:
        if rule.action_type != ACTION_TYPE_SET_CALCULATION_PARAMETER:
            continue
        if rule.source_product_id not in present_ids:
            continue
        key, value = rule.parameter_key, rule.value
        if key is None or value is None:
            continue
        if key not in overrides or value > overrides[key]:
            overrides[key] = value
    return overrides


def resolve_engineering_notes(items: list[dict], technical_rules: list[TechnicalRule]) -> list[str]:
    """Motor 4 → Motor 6: notas de `TechnicalRule` de tipo `flag_engineering_note` cuyo
    `source_product_id` está presente en `items`, para agregar al borrador de ingeniería
    generado por IA (ver api/routers/ai.py). Sin duplicados; conserva el orden en que se
    encontraron las reglas."""
    present_ids = _present_product_ids(items)
    notes: list[str] = []
    seen: set[str] = set()
    for rule in technical_rules:
        if rule.action_type != ACTION_TYPE_FLAG_ENGINEERING_NOTE:
            continue
        if rule.source_product_id not in present_ids:
            continue
        note = rule.engineering_note
        if note and note not in seen:
            seen.add(note)
            notes.append(note)
    return notes
