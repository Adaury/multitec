"""Puntos marcados sobre las fotos del levantamiento → cantidades exactas para la cotización.

El técnico toca la foto donde irá cada equipo y le pone un tipo (cámara, NVR, switch...). Eso es más fiable que lo
que la IA entiende de un texto: se cuentan los puntos por tipo, se le dan a la IA como dato fijo y, ya armada la
cotización, se revisa que cuadre. Si el técnico marcó 6 cámaras y la cotización trae 4, se corrige (cuando hay una sola
línea de cámaras) o se avisa."""

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.survey import Survey, SurveyMarker

# clave -> (nombre para mostrar, patrón que reconoce el tipo en una etiqueta o en una categoría del catálogo)
POINT_KINDS: dict[str, tuple[str, str | None]] = {
    "camara": ("Cámara", r"c[áa]mara|cctv|\bdomo\b|bullet|\bptz\b"),
    "grabador": ("NVR / DVR", r"\bnvr\b|\bdvr\b|grabador"),
    "switch": ("Switch", r"\bswitch(es)?\b"),
    "gabinete": ("Gabinete / rack", r"gabinete|\brack\b"),
    "punto_red": ("Punto de red / WiFi", r"punto de red|access point|\brouter\b|\bwifi\b|\bwi-fi\b|\bap\b"),
    "acceso": ("Cerradura / lector", r"cerradura|lector|control de acceso|huella|chapa|cerco"),
    "sensor": ("Sensor / alarma", r"sensor|alarma|sirena|panel de alarma|detector"),
    "otro": ("Otro", None),
}
POINT_KIND_KEYS = tuple(POINT_KINDS)

# Líneas que mencionan el equipo pero son accesorios: no cuentan como «la cámara» al revisar cantidades.
_ACCESSORY_WORDS = re.compile(
    r"fuente|cable|conector|soporte|caja|base\b|balun|adaptador|disco|ba[ñn]o|jack|patch|canaleta|tubo|mano de obra"
    r"|instalaci[óo]n|licencia|cubierta|ventilador|\bkit\b|paquete|combo",
    re.IGNORECASE,
)


def kind_label(kind: str) -> str:
    return POINT_KINDS.get(kind, POINT_KINDS["otro"])[0]


def infer_kind(label: str | None) -> str:
    """Tipo de un punto sin tipo explícito (marcadores anteriores): se deduce del nombre que le puso el técnico."""
    text = (label or "").lower()
    for key, (_name, pattern) in POINT_KINDS.items():
        if pattern and re.search(pattern, text):
            return key
    return "otro"


def marker_kind(marker: SurveyMarker) -> str:
    return marker.kind if marker.kind in POINT_KINDS else infer_kind(marker.label)


def marker_counts(db: Session, project_id: int) -> dict[str, int]:
    """Cuántos puntos hay marcados por tipo en todas las fotos del levantamiento."""
    survey = db.query(Survey).filter(Survey.project_id == project_id).one_or_none()
    counts: dict[str, int] = {}
    if survey is None:
        return counts
    for asset in survey.assets:
        if asset.kind != "photo":
            continue
        for marker in asset.markers:
            key = marker_kind(marker)
            counts[key] = counts.get(key, 0) + 1
    return counts


def points_context(counts: dict[str, int]) -> str:
    """Bloque de texto para el contexto de la IA: cantidades exactas, no una interpretación."""
    if not counts:
        return ""
    lines = ["\n== Puntos marcados en las fotos del levantamiento (cantidades EXACTAS: úsalas tal cual) =="]
    lines += [f"- {kind_label(key)}: {n}" for key, n in counts.items() if n]
    return "\n".join(lines)


@dataclass
class Reconciliation:
    items: list[dict]
    warnings: list[str]


def is_kind_line(item: dict, kind: str, category_of: dict[int, str | None]) -> bool:
    pattern = POINT_KINDS[kind][1]
    if not pattern:
        return False
    description = str(item.get("description") or "")
    category = category_of.get(item.get("product_id") or -1) or ""
    if re.search(pattern, category, re.IGNORECASE):
        return True
    return bool(re.search(pattern, description, re.IGNORECASE)) and not _ACCESSORY_WORDS.search(description)


def reconcile_items(items: list[dict], counts: dict[str, int], category_of: dict[int, str | None]) -> Reconciliation:
    """Compara lo cotizado con lo marcado. Si lo marcado es MÁS y hay una sola línea de ese equipo, se sube a lo marcado;
    si hay varias líneas o es MENOS, solo se avisa (el técnico pudo describir más equipos de palabra)."""
    items = [dict(item) for item in items]
    warnings: list[str] = []
    for kind, marked in counts.items():
        if kind == "otro" or not marked:
            continue
        lines = [item for item in items if is_kind_line(item, kind, category_of)]
        quoted = sum(float(item.get("quantity") or 0) for item in lines)
        name = kind_label(kind)
        if not lines:
            warnings.append(
                f"Marcaste {marked} punto(s) de «{name}» en las fotos pero la cotización no trae ese equipo: agrégalo."
            )
        elif quoted < marked:
            if len(lines) == 1:
                lines[0]["quantity"] = float(marked)
                warnings.append(
                    f"Se ajustó «{lines[0].get('description')}» de {quoted:g} a {marked} según los puntos marcados en las fotos."
                )
            else:
                warnings.append(
                    f"Marcaste {marked} punto(s) de «{name}» en las fotos y la cotización suma {quoted:g}: revisa las cantidades."
                )
        elif quoted > marked:
            warnings.append(
                f"La cotización trae {quoted:g} de «{name}» y en las fotos hay {marked} marcados: confirma que no sobren."
            )
    return Reconciliation(items=items, warnings=warnings)
