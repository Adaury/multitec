import pytest

from app.ai_engine import conversation
from app.ai_engine.conversation import classify_by_rules, extract_client_name, match_project, understand
from tests.conftest import auth_headers, make_project

TYPES = ["Cámaras de seguridad (CCTV)", "Alarma", "Control de acceso", "Redes y cableado", "Otro"]


@pytest.fixture(autouse=True)
def _no_model(monkeypatch):
    """Por defecto la IA "no responde": así se prueba que las reglas bastan y que nada se inventa."""
    monkeypatch.setattr(conversation, "classify_with_model", lambda text: (None, ""))


@pytest.mark.parametrize(
    "phrase, intent",
    [
        ("Vamos a hacer un levantamiento de cámaras para Juan Pérez", "new_survey"),
        ("quiero cotizarle una alarma a la señora Marta", "new_survey"),
        ("unas cámaras para el colmado", "new_survey"),
        ("continuar con Ferretería López", "open_project"),
        ("voy a terminar lo de ayer", "open_project"),
        ("qué tengo hoy", "agenda"),
        ("¿Qué me toca?", "agenda"),
        ("enséñame las cotizaciones", "quotes"),
        ("tengo que atender un ticket", "tickets"),
        ("hay una avería donde Pedro", "tickets"),
        ("me toca ir a casa de la doctora Jiménez a medir", "new_survey"),
        ("hay que visitar a don Ramón", "new_survey"),
        ("nada por ahora", "none"),
        ("bla bla bla", None),
    ],
)
def test_rules_classify_what_technicians_say(phrase, intent):
    assert classify_by_rules(phrase) == intent


@pytest.mark.parametrize(
    "phrase, name",
    [
        ("un levantamiento de cámaras para Juan Pérez", "Juan Pérez"),
        ("levantamiento para el cliente maría gómez de alarma", "María Gómez"),
        ("el cliente se llama Pedro Martínez, 809 555 1234", "Pedro Martínez"),
        ("cotizar unas cámaras para el señor Luis en Santiago", "Luis"),
        ("me toca ir a casa de la doctora Jiménez a medir", "Jiménez"),
        ("hay que visitar a don Ramón Castillo", "Ramón Castillo"),
        ("un levantamiento para cámaras", ""),
        ("un levantamiento", ""),
    ],
)
def test_client_name_is_pulled_out_of_a_free_sentence(phrase, name):
    assert extract_client_name(phrase) == name


def test_project_match_needs_the_whole_name_or_two_words():
    projects = [
        {"project_id": 1, "project_code": "PRY-1", "client_name": "Ferretería López"},
        {"project_id": 2, "project_code": "PRY-2", "client_name": "Juan Pérez"},
    ]

    assert match_project("continuar con ferreteria lopez", projects)["project_id"] == 1
    assert match_project("sigo con lo de Juan Pérez", projects)["project_id"] == 2
    assert match_project("continuar con Juan", projects) is None  # un solo nombre no basta


def test_understand_fills_type_and_phone_for_a_new_survey():
    result = understand("levantamiento de cámaras para Ana Díaz, 809 555 1234", TYPES, [])

    assert result["intent"] == "new_survey"
    assert result["client_name"] == "Ana Díaz"
    assert result["survey_type"] == "Cámaras de seguridad (CCTV)"
    assert result["phone"] == "809-555-1234"
    assert result["ai_used"] is False


def test_model_is_only_asked_when_rules_do_not_know(monkeypatch):
    calls = []

    def fake(text):
        calls.append(text)
        return "new_survey", "Carlos Ruiz"

    monkeypatch.setattr(conversation, "classify_with_model", fake)

    known = understand("qué tengo hoy", TYPES, [])
    unknown = understand("Carlos Ruiz me escribió por lo del portón", TYPES, [])

    assert known["intent"] == "agenda" and known["ai_used"] is False
    assert calls == ["Carlos Ruiz me escribió por lo del portón"]
    assert unknown["intent"] == "new_survey" and unknown["client_name"] == "Carlos Ruiz"
    assert unknown["ai_used"] is True


# ---------------------------------------------------------------- endpoint


def _talk(client, headers, text):
    resp = client.post("/api/assistant/talk", json={"text": text, "survey_types": TYPES}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_talk_requires_authentication(client):
    assert client.post("/api/assistant/talk", json={"text": "hola"}).status_code in (401, 403)


def test_new_survey_for_a_new_client(client, admin_token):
    body = _talk(client, auth_headers(admin_token), "un levantamiento de alarma para Rosa Méndez")

    assert body["intent"] == "new_survey"
    assert body["navigate_to"] == "/nuevo"
    assert body["client_name"] == "Rosa Méndez" and body["client_id"] is None
    assert body["survey_type"] == "Alarma"
    assert "Rosa Méndez" in body["reply"]


def test_new_survey_recognizes_an_existing_client(client, admin_token):
    headers = auth_headers(admin_token)
    existing = client.post("/api/clients", json={"name": "Rosa Méndez"}, headers=headers).json()

    body = _talk(client, headers, "levantamiento de cámaras para rosa méndez")

    assert body["client_id"] == existing["id"]
    assert "ya es cliente" in body["reply"]


def test_continue_opens_the_named_project_or_asks_which(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers, client_name="Ferretería López")

    found = _talk(client, headers, "continuar con Ferretería López")
    missing = _talk(client, headers, "continuar con lo de ayer")

    assert found["navigate_to"] == f"/proyectos/{project['id']}"
    assert project["code"] in found["reply"]
    assert missing["intent"] == "ask_project" and missing["navigate_to"] is None


def test_agenda_says_what_there_is_and_changes_nothing(client, admin_token):
    headers = auth_headers(admin_token)
    before = len(client.get("/api/projects", headers=headers).json())

    body = _talk(client, headers, "qué tengo hoy")

    assert body["intent"] == "agenda" and body["navigate_to"] is None
    assert "Hoy" in body["reply"]
    assert len(client.get("/api/projects", headers=headers).json()) == before


def test_unknown_phrase_asks_to_repeat_with_examples(client, admin_token):
    body = _talk(client, auth_headers(admin_token), "bla bla bla")

    assert body["intent"] == "unknown" and body["navigate_to"] is None
    assert "Puedes decirme" in body["reply"]


# ---------------------------------------------------------------- turno hablado (/listen)


def _listen(client, headers, monkeypatch, heard, content_type="audio/mp4", filename="turno.m4a"):
    import io
    import json

    from app.api.routers import assistant

    seen = {}

    def fake_transcribe(path, initial_prompt=""):
        seen["suffix"] = str(path)[-4:]
        seen["prompt"] = initial_prompt
        return heard

    monkeypatch.setattr(assistant, "transcribe_audio", fake_transcribe)
    resp = client.post(
        "/api/assistant/listen",
        files={"audio": (filename, io.BytesIO(b"\x00" * 4000), content_type)},
        data={"survey_types": json.dumps(TYPES)},
        headers=headers,
    )
    return resp, seen


def test_spoken_turn_is_transcribed_and_answered_like_a_typed_one(client, admin_token, monkeypatch):
    resp, seen = _listen(client, auth_headers(admin_token), monkeypatch, "Un levantamiento de alarma para Rosa Méndez.")

    body = resp.json()
    assert resp.status_code == 200, resp.text
    assert body["heard"] == "Un levantamiento de alarma para Rosa Méndez."
    assert body["intent"] == "new_survey" and body["client_name"] == "Rosa Méndez"
    assert body["survey_type"] == "Alarma"
    assert seen["suffix"] == ".m4a"  # iPhone graba mp4/aac: la extensión se conserva para decodificar
    assert "asistente" in seen["prompt"]  # vocabulario de conversación, no el de levantamiento


def test_silence_asks_to_repeat_instead_of_guessing(client, admin_token, monkeypatch):
    resp, _ = _listen(client, auth_headers(admin_token), monkeypatch, "   ")

    assert resp.status_code == 200
    assert resp.json()["intent"] == "unheard"
    assert "repites" in resp.json()["reply"]


def test_listen_rejects_files_that_are_not_audio(client, admin_token, monkeypatch):
    resp, _ = _listen(
        client, auth_headers(admin_token), monkeypatch, "hola", content_type="application/pdf", filename="x.pdf"
    )

    assert resp.status_code == 400


def test_listen_requires_authentication(client):
    import io

    resp = client.post("/api/assistant/listen", files={"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")})
    assert resp.status_code in (401, 403)
