import json
from pathlib import Path

import ollama
from fastapi import HTTPException

from app.core.config import get_settings

SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGES = 6


def get_client() -> ollama.Client:
    settings = get_settings()
    return ollama.Client(host=settings.ollama_host)


def _call(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=(
                "Ollama no está corriendo o falta un modelo. Instala Ollama desde "
                "https://ollama.com, luego ejecuta 'ollama pull llama3.2' y "
                f"'ollama pull llava'. Detalle: {e}"
            ),
        )


def load_image_paths(file_paths: list[str], limit: int = MAX_IMAGES) -> list[str]:
    """Filtra fotos del disco a formatos soportados por el modelo de visión local.

    Omite formatos no soportados (p. ej. HEIC de iPhone) en vez de fallar — el análisis
    continúa solo con las imágenes compatibles.
    """
    paths: list[str] = []
    for path_str in file_paths:
        if len(paths) >= limit:
            break
        path = Path(path_str)
        if path.suffix.lower() in SUPPORTED_IMAGE_TYPES and path.exists():
            paths.append(str(path))
    return paths


REFUSAL_MARKERS = (
    "lo siento",
    "disculpe",
    "no puedo ayudarte",
    "no puedo proporcionar",
    "no puedo procesar",
    "no puedo describir",
    "no contiene imagen",
    "no contiene imágenes",
    "no hay imagen",
    "no hay imágenes",
    "no hay ninguna imagen",
    "sin imagen adjunta",
    "sin imágenes adjuntas",
    "no imágenes adjuntas",
    "no veo ninguna imagen",
    "no veo imagen",
    "no se proporcionó ninguna imagen",
    "no proporcionaste imagen",
    "asegúrate de agregarlas",
)

# Frases que casi nunca aparecen al inicio de una descripción real de imagen, sin importar
# qué tan larga sea la negativa (p. ej. negativas "por sensibilidad" con explicaciones largas).
OPENING_REFUSAL_MARKERS = ("lo siento", "disculpe", "no puedo")


def _looks_like_refusal(text: str) -> bool:
    """El modelo de visión local (llava, 7B cuantizado en CPU) a veces produce falsos
    positivos de negativa ante fotos de cámaras/seguridad, o pierde la imagen de vista con
    prompts largos. Se detecta heurísticamente para reintentar en vez de mostrar basura."""
    lowered = text.strip().lower()
    if any(marker in lowered[:40] for marker in OPENING_REFUSAL_MARKERS):
        return True
    return len(lowered) < 220 and any(marker in lowered for marker in REFUSAL_MARKERS)


def summarize_survey(notes: str, measurements: str, observations: str, image_paths: list[str]) -> str:
    settings = get_settings()
    client = get_client()

    notes_block = (
        f"Notas: {notes or '(sin notas)'}\n"
        f"Medidas: {measurements or '(sin medidas)'}\n"
        f"Observaciones: {observations or '(sin observaciones)'}"
    )
    photos = load_image_paths(image_paths)

    if not photos:
        text = (
            "Organiza la siguiente información de un levantamiento técnico de seguridad "
            "electrónica (CCTV, redes, control de acceso, etc.) en un resumen profesional y "
            "claro en español, en párrafos cortos. No inventes datos que no estén presentes.\n\n"
            + notes_block
        )

        def run_text_only():
            response = client.chat(model=settings.ai_model, messages=[{"role": "user", "content": text}])
            return response.message.content or ""

        return _call(run_text_only)

    # El modelo de visión responde mejor cuando la instrucción sobre la foto va primero;
    # con el texto del levantamiento por delante tiende a "olvidar" que hay una imagen.
    vision_text = (
        "Estas fotos son de un levantamiento técnico de seguridad electrónica (CCTV, redes, "
        "control de acceso, etc.). Descríbelas brevemente. Luego organiza esta información "
        "adicional en un resumen profesional en español, en párrafos cortos, sin inventar "
        "datos que no estén presentes:\n\n" + notes_block
    )
    message = {"role": "user", "content": vision_text, "images": photos}

    def run_vision():
        response = client.chat(model=settings.ai_vision_model, messages=[message])
        return response.message.content or ""

    result = _call(run_vision)
    if _looks_like_refusal(result):
        result = _call(run_vision)  # reintento único: la negativa suele ser aleatoria, no consistente

    if _looks_like_refusal(result):
        # El modelo de visión local no logró analizar la foto tras dos intentos — se degrada
        # a un resumen de solo texto en vez de mostrarle al usuario una negativa sin sentido.
        text = (
            "Organiza la siguiente información de un levantamiento técnico de seguridad "
            "electrónica en un resumen profesional y claro en español, en párrafos cortos. "
            "No inventes datos que no estén presentes.\n\n" + notes_block
        )

        def run_text_fallback():
            response = client.chat(model=settings.ai_model, messages=[{"role": "user", "content": text}])
            content = response.message.content or ""
            return content + "\n\n(No se pudo analizar la(s) foto(s) adjunta(s) con el modelo de visión local; solo se resumió el texto.)"

        result = _call(run_text_fallback)

    return result


ENGINEERING_SCHEMA = {
    "type": "object",
    "properties": {
        "recommended_equipment": {"type": "string"},
        "distribution": {"type": "string"},
        "conduits": {"type": "string"},
        "wiring": {"type": "string"},
        "technical_design": {"type": "string"},
        "observations": {"type": "string"},
    },
    "required": [
        "recommended_equipment",
        "distribution",
        "conduits",
        "wiring",
        "technical_design",
        "observations",
    ],
}


def draft_engineering(project_context: str) -> dict:
    settings = get_settings()
    client = get_client()

    prompt = (
        "Eres un ingeniero de sistemas de seguridad electrónica. A partir del siguiente "
        "expediente de proyecto, redacta un borrador de ingeniería técnica en español. "
        "Sé concreto y práctico; si falta información para alguna sección, indícalo "
        "brevemente en vez de inventar.\n\n" + project_context
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=ENGINEERING_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.message.content)

    return _call(run)


BUDGET_SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                },
                "required": ["product_id", "description", "quantity"],
            },
        }
    },
    "required": ["items"],
}


def suggest_budget_items(project_context: str, catalog: list[dict]) -> list[dict]:
    settings = get_settings()
    client = get_client()

    catalog_text = "\n".join(f"- id={p['id']}: {p['name']} ({p['category']})" for p in catalog)
    prompt = (
        "Eres un especialista en seguridad electrónica armando un presupuesto. A partir del "
        "expediente del proyecto, sugiere una lista de materiales necesarios con cantidades. "
        "SOLO puedes usar productos de este catálogo (usa su id exacto en product_id); si "
        "necesitas algo que no está en el catálogo (por ejemplo mano de obra o servicios), "
        "pon product_id en 0 y descríbelo en description.\n\n"
        f"Catálogo disponible:\n{catalog_text}\n\n"
        f"Expediente del proyecto:\n{project_context}"
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=BUDGET_SUGGESTION_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
        )
        items = json.loads(response.message.content)["items"]
        for item in items:
            if item.get("product_id") == 0:
                item["product_id"] = None
        return items

    return _call(run)


def answer_question(project_context: str, question: str) -> str:
    settings = get_settings()
    client = get_client()

    def run():
        response = client.chat(
            model=settings.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente que responde preguntas sobre proyectos de "
                        "seguridad electrónica usando únicamente la información de los "
                        "expedientes proporcionados (puede haber uno o varios, separados por "
                        "'---'). Si la respuesta no está en los expedientes, dilo claramente "
                        "en vez de inventar. Si hay varios proyectos, aclara a cuál te "
                        "refieres en la respuesta.\n\n"
                        f"Expediente(s):\n{project_context}"
                    ),
                },
                {"role": "user", "content": question},
            ],
        )
        return response.message.content or ""

    return _call(run)
