"""Comparar una cotización ajena (competidor o proveedor) con el levantamiento y con la cotización propia.

Dos partes bien separadas:
  1. LEER el documento (PDF con texto o foto) y sacar sus líneas: aquí interviene la IA, por eso oficina puede corregir
     lo que entendió antes de fiarse del resultado.
  2. COMPARAR: sin IA, con reglas fijas, así el resultado es el mismo cada vez y se puede explicar línea por línea."""

import io
import json
import re
import unicodedata
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.core.config import get_settings
from app.models.product import Product
from app.models.quote import Quote
from app.services.survey_points import POINT_KINDS, is_kind_line, kind_label, marker_counts

MAX_PDF_PAGES = 12
MAX_TEXT_CHARS = 14000
PRICE_TOLERANCE = 0.01  # 1 %: por debajo de esto el precio se da por igual
MATCH_THRESHOLD = 0.34

ITEMS_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                },
                "required": ["description", "quantity", "unit_price"],
            },
        },
        "total": {"type": ["number", "null"]},
    },
    "required": ["items"],
}


# ---------------------------------------------------------------- 1. leer el documento


def extract_text(contents: bytes, content_type: str) -> str:
    """Texto de un PDF (con texto, no escaneado) o de una foto (la lee el modelo de visión)."""
    base = (content_type or "").split(";")[0].strip().lower()
    if base == "application/pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(contents))
            pages = [(page.extract_text() or "") for page in reader.pages[:MAX_PDF_PAGES]]
        except Exception:
            raise HTTPException(status_code=400, detail="No se pudo leer ese PDF. Súbelo como foto o pega el texto.")
        text = "\n".join(pages).strip()
        if len(text) < 20:
            raise HTTPException(
                status_code=400,
                detail="Ese PDF no tiene texto legible (parece escaneado). Súbelo como foto o pega el texto.",
            )
        return text[:MAX_TEXT_CHARS]

    settings = get_settings()
    client = get_client()
    prompt = (
        "Transcribe el texto de esta cotización o factura tal como aparece, una línea por producto, con su "
        "descripción, cantidad y precio unitario. Incluye el total si aparece. No inventes nada que no se vea."
    )

    def run():
        response = client.chat(
            model=settings.ai_vision_model,
            messages=[{"role": "user", "content": prompt, "images": [contents]}],
            options=OLLAMA_OPTIONS,
        )
        return (response.message.content or "").strip()

    text = _call(run)
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="No pude leer texto en esa foto. Prueba con otra o pega el texto.")
    return text[:MAX_TEXT_CHARS]


@dataclass
class ExtractedQuote:
    items: list[dict] = field(default_factory=list)
    total: float | None = None


def clean_items(raw_items: list[dict]) -> list[dict]:
    """Solo líneas utilizables: con descripción, cantidad positiva y precio no negativo."""
    out = []
    for raw in raw_items:
        try:
            description = str(raw.get("description") or "").strip()[:300]
            quantity = float(raw.get("quantity") or 0)
            price = float(raw.get("unit_price") or 0)
        except (TypeError, ValueError):
            continue
        if description and quantity > 0 and price >= 0:
            out.append({"description": description, "quantity": quantity, "unit_price": price})
    return out


def read_items(text: str) -> ExtractedQuote:
    """Pasa el texto de la cotización a líneas (descripción, cantidad, precio unitario)."""
    settings = get_settings()
    client = get_client()
    prompt = (
        "Del siguiente texto de una cotización, saca cada línea de producto o servicio con su descripción, "
        "cantidad y precio UNITARIO (si solo trae el total de la línea, divídelo entre la cantidad). Los precios son en "
        "pesos dominicanos salvo que diga otra cosa. Ignora encabezados, datos del cliente y condiciones. Pon también "
        "el total del documento si aparece, o null.\n\n" + text
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=ITEMS_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options=OLLAMA_OPTIONS,
        )
        return json.loads(response.message.content)

    data = _call(run)
    total = data.get("total")
    try:
        total = float(total) if total is not None else None
    except (TypeError, ValueError):
        total = None
    return ExtractedQuote(items=clean_items(data.get("items") or []), total=total)


# ---------------------------------------------------------------- 2. comparar

_STOPWORDS = {"de", "del", "la", "el", "los", "las", "para", "con", "y", "en", "un", "una", "por", "x", "ud", "und", "unidad"}


def _tokens(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return {t for t in re.findall(r"[a-z0-9]+", plain) if t not in _STOPWORDS and len(t) > 1}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _price_state(ext_price: float, our_price: float) -> str:
    if our_price == 0 and ext_price == 0:
        return "igual"
    base = our_price or ext_price
    return "igual" if abs(ext_price - our_price) / base <= PRICE_TOLERANCE else ("mas_caro" if ext_price > our_price else "mas_barato")


@dataclass
class Comparison:
    matched: list[dict]
    only_external: list[dict]
    only_ours: list[dict]
    coverage: list[dict]
    totals: dict


def compare(db: Session, project_id: int, ext_items: list[dict], ext_total: float | None, quote: Quote | None) -> Comparison:
    ours = (
        [
            {"description": i.description, "quantity": float(i.quantity), "unit_price": float(i.unit_price), "product_id": i.product_id}
            for i in quote.items
        ]
        if quote
        else []
    )

    # Emparejamiento uno a uno, de la pareja más parecida a la menos parecida.
    scored = sorted(
        (
            (similarity(e["description"], o["description"]), ei, oi)
            for ei, e in enumerate(ext_items)
            for oi, o in enumerate(ours)
        ),
        reverse=True,
    )
    used_e: set[int] = set()
    used_o: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    for score, ei, oi in scored:
        if score < MATCH_THRESHOLD or ei in used_e or oi in used_o:
            continue
        used_e.add(ei)
        used_o.add(oi)
        pairs.append((ei, oi, score))

    matched = []
    for ei, oi, score in sorted(pairs):
        e, o = ext_items[ei], ours[oi]
        same_qty = abs(e["quantity"] - o["quantity"]) < 0.01
        price = _price_state(e["unit_price"], o["unit_price"])
        matched.append(
            {
                "external": e,
                "ours": {k: o[k] for k in ("description", "quantity", "unit_price")},
                "same_quantity": same_qty,
                "price": price,
                "price_diff_pct": round((e["unit_price"] - o["unit_price"]) / (o["unit_price"] or e["unit_price"] or 1) * 100, 1),
                "status": "igual" if same_qty and price == "igual" else "diferente",
            }
        )
    only_external = [e for i, e in enumerate(ext_items) if i not in used_e]
    only_ours = [{k: o[k] for k in ("description", "quantity", "unit_price")} for i, o in enumerate(ours) if i not in used_o]

    # Cobertura del levantamiento: lo que el técnico marcó en las fotos frente a lo que trae cada cotización.
    category_of = {}
    ids = {o["product_id"] for o in ours if o["product_id"] is not None}
    if ids:
        category_of = {p.id: p.category_name for p in db.query(Product).filter(Product.id.in_(ids)).all()}
    coverage = []
    for kind, marked in marker_counts(db, project_id).items():
        if kind == "otro" or kind not in POINT_KINDS:
            continue
        ext_qty = sum(e["quantity"] for e in ext_items if is_kind_line(e, kind, {}))
        our_qty = sum(o["quantity"] for o in ours if is_kind_line(o, kind, category_of))
        coverage.append(
            {
                "kind": kind,
                "label": kind_label(kind),
                "marked": marked,
                "external": ext_qty,
                "ours": our_qty,
                "external_status": "ok" if ext_qty == marked else ("falta" if ext_qty < marked else "sobra"),
                "ours_status": "ok" if our_qty == marked else ("falta" if our_qty < marked else "sobra"),
            }
        )

    ext_subtotal = round(sum(e["quantity"] * e["unit_price"] for e in ext_items), 2)
    totals = {
        "external_subtotal": ext_subtotal,
        "external_total": ext_total,
        "our_subtotal": float(quote.subtotal) if quote else None,
        "our_total": float(quote.total) if quote else None,
        "our_code": quote.code if quote else None,
    }
    return Comparison(matched, only_external, only_ours, coverage, totals)
