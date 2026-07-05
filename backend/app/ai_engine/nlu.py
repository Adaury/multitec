"""Motor 1 — Interpretación del lenguaje (§ docs/ai-engine-architecture.md).

Convierte el texto/voz/fotos crudos de un levantamiento en un resumen legible
(`summarize_survey`) o en entidades estructuradas (`interpret_survey_items`). No conoce el
catálogo — resolver una entidad contra un producto real es responsabilidad de Motor 2
(`app.ai_engine.catalog_matching`).
"""

import json

from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client, load_image_paths, looks_like_refusal
from app.core.config import get_settings


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
            response = client.chat(
                model=settings.ai_model, messages=[{"role": "user", "content": text}], options=OLLAMA_OPTIONS
            )
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
        response = client.chat(model=settings.ai_vision_model, messages=[message], options=OLLAMA_OPTIONS)
        return response.message.content or ""

    result = _call(run_vision)
    if looks_like_refusal(result):
        result = _call(run_vision)  # reintento único: la negativa suele ser aleatoria, no consistente

    if looks_like_refusal(result):
        # El modelo de visión local no logró analizar la foto tras dos intentos — se degrada
        # a un resumen de solo texto en vez de mostrarle al usuario una negativa sin sentido.
        text = (
            "Organiza la siguiente información de un levantamiento técnico de seguridad "
            "electrónica en un resumen profesional y claro en español, en párrafos cortos. "
            "No inventes datos que no estén presentes.\n\n" + notes_block
        )

        def run_text_fallback():
            response = client.chat(
                model=settings.ai_model, messages=[{"role": "user", "content": text}], options=OLLAMA_OPTIONS
            )
            content = response.message.content or ""
            return content + "\n\n(No se pudo analizar la(s) foto(s) adjunta(s) con el modelo de visión local; solo se resumió el texto.)"

        result = _call(run_text_fallback)

    return result


SURVEY_ENTITIES_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string"},
                },
                "required": ["description", "quantity"],
            },
        }
    },
    "required": ["entities"],
}


def interpret_survey_items(project_context: str) -> list[dict]:
    """Extrae del expediente del proyecto los materiales, equipos, accesorios o mano de
    obra mencionados explícitamente por el técnico, con su cantidad — sin intentar
    resolverlos todavía contra el catálogo real (eso lo hace
    `catalog_matching.match_entities_to_catalog`). Separar este paso permite conservar una
    entidad detectada aunque no exista producto de catálogo para ella, en vez de que
    desaparezca silenciosamente como ocurría cuando interpretación y matching iban en una
    sola llamada al modelo."""
    settings = get_settings()
    client = get_client()

    prompt = (
        "Eres un especialista en seguridad electrónica interpretando el lenguaje de un "
        "técnico durante un levantamiento. A partir del expediente del proyecto, "
        "identifica cada material, equipo, accesorio o servicio de mano de obra "
        "mencionado EXPLÍCITAMENTE, con su cantidad.\n\n"
        "Reglas:\n"
        "1. Convierte cantidades escritas en palabras a números (\"ocho cámaras\" → 8, "
        "\"doscientos metros\" → 200, \"diez\" → 10).\n"
        "2. Incluye SOLO lo que el técnico menciona explícitamente, con la cantidad que "
        "él indique — no agregues accesorios ni productos por tu cuenta; eso se calcula "
        "aparte con reglas del catálogo.\n"
        "3. Usa la descripción tal como la usó el técnico, sin intentar normalizarla "
        "contra ningún catálogo — eso es un paso aparte.\n\n"
        f"Expediente del proyecto:\n{project_context}"
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=SURVEY_ENTITIES_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options=OLLAMA_OPTIONS,
        )
        return json.loads(response.message.content)["entities"]

    return _call(run)
