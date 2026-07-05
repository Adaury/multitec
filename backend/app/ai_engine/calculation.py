"""Motor 5 — Motor de cálculos (§ docs/ai-engine-architecture.md).

Calculadoras implementadas: margen de desperdicio de cable (`apply_cable_waste_margin`),
mano de obra (`calculate_labor` + `build_labor_budget_item`) y almacenamiento
(`calculate_storage`). `CapacityCalculator` queda para cuando exista el dato que necesita
(capacidad de canal de NVR/switch) — ver el plan de evolución del documento de arquitectura.
"""

import math

from sqlalchemy.orm import Session

from app.models.calculation_parameter import CalculationParameter

CABLE_TAG = "cable"

CABLE_WASTE_MARGIN_KEY = "cable_waste_margin_pct"
LABOR_HOURLY_RATE_KEY = "labor_hourly_rate"
LABOR_MAX_HOURS_PER_TECHNICIAN_KEY = "labor_max_hours_per_technician"
STORAGE_GB_PER_MP_PER_DAY_KEY = "storage_gb_per_megapixel_per_day"
STORAGE_RETENTION_DAYS_KEY = "storage_retention_days"

LABOR_LINE_DESCRIPTION_PREFIX = "Mano de obra de instalación"

# Un parámetro conocido = uno con un consumidor real (ver abajo). Declarar una clave sin
# que nada la lea sería configuración muerta — mismo criterio que SUPPORTED_ACTION_TYPES
# en app.models.technical_rule.
KNOWN_PARAMETERS: dict[str, dict] = {
    CABLE_WASTE_MARGIN_KEY: {
        "default": 0.05,
        "description": "Margen de desperdicio aplicado al metraje de cable detectado (0.05 = 5%).",
    },
    LABOR_HOURLY_RATE_KEY: {
        "default": 200.0,
        "description": "Costo de mano de obra por hora de instalación, por técnico (RD$/hora).",
    },
    LABOR_MAX_HOURS_PER_TECHNICIAN_KEY: {
        "default": 40.0,
        "description": (
            "Horas de instalación que se le asignan a un solo técnico antes de sumar otro "
            "(ej. 40 = una semana laboral)."
        ),
    },
    STORAGE_GB_PER_MP_PER_DAY_KEY: {
        "default": 15.0,
        "description": (
            "Estimación de espacio en disco por megapixel de resolución de cámara, por día "
            "de grabación continua (GB/MP/día) — aproximación de planeación, no un cálculo "
            "exacto de bitrate/codec."
        ),
    },
    STORAGE_RETENTION_DAYS_KEY: {
        "default": 30.0,
        "description": "Días de retención de grabación que debe soportar el almacenamiento.",
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


def calculate_labor(
    items: list[dict],
    install_profiles: dict[int, tuple[float | None, str | None]],
    hourly_rate: float,
    max_hours_per_technician: float,
) -> dict | None:
    """Estima horas de instalación, cantidad de técnicos y costo de mano de obra a partir
    de `install_minutes`/`labor_role` de Motor 2 (§ docs/ai-engine-architecture.md).

    `install_profiles` mapea product_id -> (install_minutes, labor_role), tal como lo
    tiene el caller ya cargado desde `Product` (ver api/routers/ai.py) — un producto
    ausente o con `install_minutes` nulo simplemente no aporta horas (dato sin cargar
    todavía en ese producto, no un error). Devuelve `None` si no hay ninguna hora que
    estimar, para que el caller no agregue una línea de "0 horas" al presupuesto.

    El costo de mano de obra es horas totales × tarifa, sin importar cuántos técnicos se
    repartan el trabajo (se paga por hora-persona trabajada, no por técnico); la cantidad
    de técnicos es solo para dimensionar el proyecto — cuántos hacen falta para no exceder
    `max_hours_per_technician` cada uno. `labor_role` se usa para desglosar las horas por
    tipo de técnico en la descripción de la línea, no para aplicar tarifas distintas por
    rol — eso requeriría una tarifa configurable por rol, que no existe todavía.
    """
    hours_by_role: dict[str, float] = {}
    total_minutes = 0.0

    for item in items:
        product_id = item.get("product_id")
        if product_id is None or product_id not in install_profiles:
            continue
        install_minutes, labor_role = install_profiles[product_id]
        if not install_minutes:
            continue
        minutes = install_minutes * (item.get("quantity") or 0)
        if minutes <= 0:
            continue
        total_minutes += minutes
        role_label = labor_role or "Sin rol asignado"
        hours_by_role[role_label] = hours_by_role.get(role_label, 0.0) + minutes / 60

    if total_minutes <= 0:
        return None

    total_hours = round(total_minutes / 60, 2)
    technician_count = math.ceil(total_hours / max_hours_per_technician) if max_hours_per_technician else 1
    technician_count = max(1, technician_count)

    return {
        "total_hours": total_hours,
        "technician_count": technician_count,
        "hourly_rate": hourly_rate,
        "labor_cost": round(total_hours * hourly_rate, 2),
        "hours_by_role": {role: round(hours, 2) for role, hours in hours_by_role.items()},
    }


def build_labor_budget_item(estimate: dict) -> dict:
    """Convierte el resultado de `calculate_labor` en una línea más de presupuesto —
    mismo formato sin catálogo (`product_id=None`) que ya usan mano de obra/servicios
    mencionados a mano por el técnico."""
    role_breakdown = ", ".join(f"{role}: {hours}h" for role, hours in estimate["hours_by_role"].items())
    description = (
        f"{LABOR_LINE_DESCRIPTION_PREFIX} — {estimate['technician_count']} técnico(s), "
        f"{estimate['total_hours']}h estimadas ({role_breakdown})"
    )
    return {
        "product_id": None,
        "description": description,
        "quantity": estimate["total_hours"],
        "unit_price": estimate["hourly_rate"],
    }


def calculate_storage(
    items: list[dict],
    resolution_by_product_id: dict[int, float | None],
    storage_capacity_by_product_id: dict[int, float | None],
    gb_per_mp_per_day: float,
    retention_days: float,
) -> list[dict]:
    """Corrige la cantidad de los ítems de almacenamiento ya presentes en el presupuesto
    (disco duro, NVR con disco interno — cualquier producto con `storage_capacity_gb`) a
    partir del espacio real que va a hacer falta: Σ(resolución_mp × cantidad) de las
    cámaras del presupuesto, × `gb_per_mp_per_day` × `retention_days`.

    No agrega un producto de almacenamiento si no hay ninguno en el presupuesto todavía —
    qué disco/marca comprar es una decisión de `CatalogRule`/`TechnicalRule` (Motor 4) o
    del técnico, no de esta calculadora; esta solo se asegura de que la cantidad de lo que
    ya se decidió comprar alcance. Nunca reduce una cantidad ya presente por debajo de lo
    que el técnico o una regla ya pusieron — sólo la sube si hace falta, porque
    sub-aprovisionar almacenamiento es un peor fallo que un poco de margen de más.
    """
    total_gb_needed = 0.0
    for item in items:
        product_id = item.get("product_id")
        resolution_mp = resolution_by_product_id.get(product_id) if product_id is not None else None
        if not resolution_mp:
            continue
        total_gb_needed += resolution_mp * gb_per_mp_per_day * retention_days * (item.get("quantity") or 0)

    if total_gb_needed <= 0:
        return items

    updated = []
    for item in items:
        product_id = item.get("product_id")
        capacity_gb = storage_capacity_by_product_id.get(product_id) if product_id is not None else None
        if capacity_gb:
            required_units = math.ceil(total_gb_needed / capacity_gb)
            item = {**item, "quantity": max(required_units, item.get("quantity") or 0)}
        updated.append(item)
    return updated
