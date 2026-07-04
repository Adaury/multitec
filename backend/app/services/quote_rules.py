def expand_with_suggested_accessories(items: list[dict], catalog: list[dict]) -> list[dict]:
    """Post-procesamiento determinista (sin IA) para la generación automática de
    presupuesto desde el levantamiento (§ catálogo inteligente).

    La IA (modelo local, modesto) hace bien el matching semántico de lo que el técnico
    dijo explícitamente, pero no es confiable para reglas tipo "si hay cámaras, agrega un
    NVR" — así que esa parte se resuelve aquí con datos del catálogo, no con el modelo:
    por cada ítem ya sugerido con product_id, si ese producto tiene `suggests_tags`, se
    busca en el catálogo un producto cuyas `tags` intersecten y, si no está ya incluido,
    se agrega con cantidad 1 (el usuario la ajusta después en el editor de líneas).
    """
    by_id = {p["id"]: p for p in catalog}
    included_ids = {item["product_id"] for item in items if item.get("product_id")}
    extra_items: list[dict] = []
    suggested_ids: set[int] = set()

    for item in items:
        product_id = item.get("product_id")
        if not product_id:
            continue
        product = by_id.get(product_id)
        suggest_tags = set((product or {}).get("suggests_tags") or [])
        if not suggest_tags:
            continue

        for candidate in catalog:
            if candidate["id"] in included_ids or candidate["id"] in suggested_ids:
                continue
            candidate_tags = set(candidate.get("tags") or [])
            if candidate_tags & suggest_tags:
                extra_items.append(
                    {"product_id": candidate["id"], "description": candidate["name"], "quantity": 1}
                )
                suggested_ids.add(candidate["id"])

    return items + extra_items
