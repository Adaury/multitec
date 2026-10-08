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


VOICE_SURVEY_SCHEMA = {
    "type": "object",
    "properties": {
        "notes": {"type": "string"},
        "measurements": {"type": "string"},
        "observations": {"type": "string"},
    },
    "required": ["notes", "measurements", "observations"],
}


def _format_voice_examples(examples: list[dict]) -> str:
    """Ejemplos reales de esta empresa (lo que el técnico dejó tras corregir a la IA), para que el
    modelo imite su criterio de reparto. Se serializan como JSON, igual que la salida esperada."""
    blocks = []
    for i, ex in enumerate(examples, 1):
        result = {k: ex.get(k, "") for k in ("notes", "measurements", "observations")}
        blocks.append(f"Ejemplo {i}\nDictado: {ex['transcript']}\nResultado: {json.dumps(result, ensure_ascii=False)}")
    return "\n\n".join(blocks)


def classify_voice_transcript(transcript: str, examples: list[dict] | None = None) -> dict:
    """Reparte lo que el técnico dijo en voz alta entre los tres campos del levantamiento
    (Notas, Medidas, Observaciones). Solo reorganiza y limpia muletillas — no agrega ni
    inventa datos. Si Ollama falla o devuelve algo inútil, se degrada a poner la
    transcripción completa en Notas para no perder nada; `classified` indica cuál ocurrió."""
    fallback = {"notes": transcript, "measurements": "", "observations": "", "classified": False}
    if not transcript.strip():
        return fallback

    settings = get_settings()
    client = get_client()
    prompt = (
        "Un técnico de seguridad electrónica (CCTV, redes, control de acceso) dictó en voz "
        "alta lo que ve durante un levantamiento en sitio. Tu única tarea es COPIAR cada frase "
        "del dictado al campo que le corresponde, en español:\n"
        "- notes: qué hay que instalar o hacer (equipos, cantidades, ubicaciones, trabajos).\n"
        "- measurements: distancias, alturas, metrajes y dimensiones, con su unidad.\n"
        "- observations: condiciones del sitio, riesgos, restricciones, pedidos del cliente.\n\n"
        "Reglas estrictas:\n"
        "1. Usa las mismas palabras del técnico. NO agregues verbos, frases ni datos que él no "
        "dijo (por ejemplo no escribas \"comprar\", ni \"no hay restricciones\").\n"
        "2. Conserva las cantidades y números exactos y NUNCA los omitas: \"tres cámaras\" se queda "
        "como \"tres cámaras\" (o \"3 cámaras\"), jamás como \"cámaras\".\n"
        "3. Cada frase del dictado va en UN solo campo; no repitas la misma información en dos "
        "campos.\n"
        "4. Si un campo no tiene contenido en el dictado, déjalo como \"\" (vacío). Nunca "
        "escribas \"ninguna\", \"no hay\" ni \"N/A\".\n\n"
    )
    if examples:
        prompt += (
            "Así reparte ESTA empresa lo que dictan sus técnicos (corregido por ellos mismos). "
            "Imita su criterio de qué va en cada campo y cómo lo redactan, pero sigue usando solo "
            "lo que dice el dictado nuevo:\n\n" + _format_voice_examples(examples) + "\n\n"
        )
    prompt += f"Dictado nuevo:\n{transcript}"

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=VOICE_SURVEY_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options={**OLLAMA_OPTIONS, "temperature": 0},  # copiar, no "crear": sin aleatoriedad
        )
        return json.loads(response.message.content)

    try:
        data = _call(run)
    except Exception:
        # _call ya registró el detalle (y convierte el error en HTTPException): aquí se
        # degrada en vez de fallar, porque la transcripción en sí ya se obtuvo.
        return fallback

    result = {key: str(data.get(key) or "").strip() for key in ("notes", "measurements", "observations")}
    if not any(result.values()):
        return fallback
    result["classified"] = True
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
