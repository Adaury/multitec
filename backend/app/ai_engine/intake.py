"""Alta rápida de un levantamiento: saca nombre, teléfono y tipo de levantamiento de lo que el
usuario dice o escribe ("Juan Pérez, 809 555 1234, cámaras"). Primero reglas simples y
deterministas (teléfono y tipo se detectan sin IA); la IA local solo ayuda a separar el nombre y
a entender frases libres. Si Ollama no responde, el resultado igual sale de las reglas."""

import json
import logging
import re
import unicodedata

from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.core.config import get_settings

logger = logging.getLogger("multitec.ai")

INTAKE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "company": {"type": "string"},
        "phone": {"type": "string"},
        "survey_type": {"type": "string"},
    },
    "required": ["name", "company", "phone", "survey_type"],
}

# Palabra clave del tipo -> sinónimos que dice la gente. La clave se busca dentro del nombre
# del tipo (p. ej. "cámara" dentro de "Cámaras de seguridad (CCTV)").
TYPE_SYNONYMS: dict[str, tuple[str, ...]] = {
    "cámara": ("camara", "camaras", "cctv", "video", "vigilancia", "dvr", "nvr"),
    "alarma": ("alarma", "alarmas", "sensor", "sensores", "sirena", "panico"),
    "acceso": ("acceso", "huella", "biometrico", "tarjeta", "torniquete", "cerradura", "marcador"),
    "cerco": ("cerco", "electrico", "electrificado", "perimetral"),
    "red": ("red", "redes", "cableado", "wifi", "internet", "fibra", "router", "switch"),
    "interco": ("intercomunicador", "interfon", "interfono", "portero", "videoportero", "citofono"),
}

_FILLERS = re.compile(
    r"^(?:el\s+cliente\s+(?:es|se\s+llama)|la\s+cliente\s+(?:es|se\s+llama)|cliente|se\s+llama|"
    r"mi\s+cliente\s+es|el\s+nombre\s+es|nombre|llamado|es)\s+",
    re.IGNORECASE,
)
_PHONE_CUT = re.compile(
    r"[,;.]|\s+(?:tel[eé]fono|tel|n[uú]mero|celular|cel|whatsapp|su\s+n[uú]mero|y\s+su|"
    r"para|tipo|de\s+tipo|quiere|necesita)\b",
    re.IGNORECASE,
)


def _fold(text: str) -> str:
    """Minúsculas y sin tildes, para comparar lo dictado sin importar la ortografía."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def extract_phone(text: str) -> str:
    """El número más largo de 7 a 15 dígitos del texto, formateado a la dominicana si tiene 10."""
    best = ""
    for chunk in re.findall(r"\+?\d[\d\s().-]{5,}\d", text):
        digits = re.sub(r"\D", "", chunk)
        if 7 <= len(digits) <= 15 and len(digits) > len(best):
            best = digits
    if len(best) == 11 and best.startswith("1"):
        best = best[1:]
    if len(best) == 10:
        return f"{best[:3]}-{best[3:6]}-{best[6:]}"
    return best


def match_survey_type(text: str, survey_types: list[str]) -> str:
    """El tipo de la lista que mejor encaja con lo que se dijo; "" si ninguno."""
    folded = _fold(text)
    words = set(re.findall(r"[a-z0-9]+", folded))
    for label in survey_types:
        if _fold(label) in folded:
            return label
    for key, synonyms in TYPE_SYNONYMS.items():
        if any(s in words for s in synonyms) or any(len(s) > 5 and s in folded for s in synonyms):
            for label in survey_types:
                if _fold(key) in _fold(label):
                    return label
    return ""


def extract_name(text: str) -> str:
    """El nombre al inicio de la frase, sin muletillas ni lo que viene después (teléfono, tipo)."""
    cleaned = _FILLERS.sub("", text.strip())
    cleaned = re.split(r"\d", cleaned, maxsplit=1)[0]
    cleaned = _PHONE_CUT.split(cleaned, maxsplit=1)[0]
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:-")
    return cleaned.title() if cleaned and cleaned == cleaned.lower() else cleaned


def parse_intake_rules(text: str, survey_types: list[str]) -> dict:
    return {
        "name": extract_name(text),
        "company": "",
        "phone": extract_phone(text),
        "survey_type": match_survey_type(text, survey_types),
    }


def parse_intake(text: str, survey_types: list[str]) -> dict:
    """Interpreta una frase libre. Las reglas dan la base; la IA local la completa solo donde las
    reglas no encontraron nada (nombre, empresa) y se descarta lo que no sea válido."""
    rules = parse_intake_rules(text, survey_types)
    result = {**rules, "ai_used": False}
    if not text.strip():
        return result

    settings = get_settings()
    prompt = (
        "Del siguiente texto dicho por un técnico de seguridad electrónica, extrae los datos de "
        "su cliente. Copia lo que se dijo; no inventes nada:\n"
        "- name: nombre y apellido de la persona (sin muletillas como \"el cliente se llama\").\n"
        "- company: empresa o negocio, o \"\" si no se menciona.\n"
        "- phone: teléfono tal como se dijo, o \"\" si no hay.\n"
        f"- survey_type: uno de {json.dumps(survey_types, ensure_ascii=False)}, o \"\" si no encaja.\n\n"
        f"Texto: {text}"
    )

    def run():
        # El cliente se crea aquí dentro: si Ollama no está disponible, cae a las reglas igual.
        response = get_client().chat(
            model=settings.ai_model,
            format=INTAKE_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options={**OLLAMA_OPTIONS, "temperature": 0},
        )
        return json.loads(response.message.content)

    try:
        data = _call(run)
    except Exception:
        logger.warning("Alta rápida: la IA no respondió, se usan solo las reglas")
        return result

    ai_name = str(data.get("name") or "").strip()
    ai_company = str(data.get("company") or "").strip()
    if ai_name and not result["name"]:
        result["name"] = ai_name
    elif ai_name and len(ai_name) < len(result["name"]) and _fold(ai_name) in _fold(result["name"]):
        result["name"] = ai_name  # la IA recortó restos de la frase que las reglas dejaron
    if ai_company:
        result["company"] = ai_company
    if not result["phone"]:
        result["phone"] = extract_phone(str(data.get("phone") or ""))
    ai_type = str(data.get("survey_type") or "").strip()
    if not result["survey_type"] and ai_type in survey_types:
        result["survey_type"] = ai_type
    result["ai_used"] = True
    return result
