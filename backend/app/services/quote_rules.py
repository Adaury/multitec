import math


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
