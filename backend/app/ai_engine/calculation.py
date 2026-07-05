"""Motor 5 — Motor de cálculos (§ docs/ai-engine-architecture.md).

Primera calculadora implementada: margen de desperdicio de cable
(`apply_cable_waste_margin`). Las demás (capacidad de NVR/disco, mano de obra) quedan
para cuando existan los datos de Motor 2 que necesitan (install_minutes, labor_role,
capacidad de canal) — ver el plan de evolución del documento de arquitectura.
"""

from sqlalchemy.orm import Session

from app.models.calculation_parameter import CalculationParameter

CABLE_TAG = "cable"

CABLE_WASTE_MARGIN_KEY = "cable_waste_margin_pct"

# Un parámetro conocido = uno con un consumidor real (ver abajo). Declarar una clave sin
# que nada la lea sería configuración muerta — mismo criterio que SUPPORTED_ACTION_TYPES
# en app.models.technical_rule.
KNOWN_PARAMETERS: dict[str, dict] = {
    CABLE_WASTE_MARGIN_KEY: {
        "default": 0.05,
        "description": "Margen de desperdicio aplicado al metraje de cable detectado (0.05 = 5%).",
    },
}


def get_calculation_parameter(db: Session, key: str) -> float:
    """Valor configurado en `calculation_parameters`, o el default de código si nadie lo
    ha configurado todavía — nunca falla por falta de fila."""
    row = db.query(CalculationParameter).filter(CalculationParameter.key == key).one_or_none()
    if row is not None:
        return float(row.value)
    return KNOWN_PARAMETERS[key]["default"]


def apply_cable_waste_margin(items: list[dict], catalog: list[dict], waste_margin_pct: float) -> list[dict]:
    """Aumenta la cantidad de los ítems ya resueltos cuyo producto está etiquetado como
    "cable" en el catálogo, aplicando el margen de desperdicio configurado. Ajusta la
    cantidad de la misma línea en vez de agregar una línea nueva — lo que cambia es
    cuánto cable real hay que comprar del mismo producto, no un producto adicional."""
    if not waste_margin_pct:
        return items

    cable_product_ids = {p["id"] for p in catalog if CABLE_TAG in (p.get("tags") or [])}
    if not cable_product_ids:
        return items

    return [
        {**item, "quantity": round(item["quantity"] * (1 + waste_margin_pct), 2)}
        if item.get("product_id") in cable_product_ids
        else item
        for item in items
    ]
