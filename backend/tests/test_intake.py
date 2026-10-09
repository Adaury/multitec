import pytest

from app.ai_engine import intake
from tests.conftest import auth_headers

TYPES = [
    "Cámaras de seguridad (CCTV)",
    "Alarma",
    "Control de acceso",
    "Cerco eléctrico",
    "Redes y cableado",
    "Intercomunicador / videoportero",
    "Otro",
]


def test_extract_phone_formats_ten_digits():
    assert intake.extract_phone("llámame al 809 555 1234") == "809-555-1234"
    assert intake.extract_phone("8 0 9 5 5 5 1 2 3 4") == "809-555-1234"
    assert intake.extract_phone("+1 (829) 555-9876") == "829-555-9876"
    assert intake.extract_phone("sin número") == ""
    assert intake.extract_phone("tengo 3 cámaras") == ""  # un dígito suelto no es un teléfono


@pytest.mark.parametrize(
    "text,expected",
    [
        ("quiere instalar cámaras", "Cámaras de seguridad (CCTV)"),
        ("un sistema de CCTV", "Cámaras de seguridad (CCTV)"),
        ("alarma para la casa", "Alarma"),
        ("control de acceso con huella", "Control de acceso"),
        ("cerco eléctrico perimetral", "Cerco eléctrico"),
        ("cableado de red y wifi", "Redes y cableado"),
        ("un videoportero", "Intercomunicador / videoportero"),
        ("algo que no sé", ""),
    ],
)
def test_match_survey_type(text, expected):
    assert intake.match_survey_type(text, TYPES) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Juan Pérez, 809 555 1234, cámaras", "Juan Pérez"),
        ("el cliente se llama maría gómez y su teléfono es 8095551234", "María Gómez"),
        ("Se llama Pedro Santana", "Pedro Santana"),
        ("cliente Ferretería Popular número 8295550000", "Ferretería Popular"),
    ],
)
def test_extract_name(text, expected):
    assert intake.extract_name(text) == expected


def test_parse_intake_falls_back_to_rules_when_ai_is_down(monkeypatch):
    def boom():
        raise RuntimeError("ollama caído")

    monkeypatch.setattr(intake, "get_client", boom)
    result = intake.parse_intake("Juan Pérez, 809 555 1234, instalar cámaras", TYPES)
    assert result == {
        "name": "Juan Pérez",
        "company": "",
        "phone": "809-555-1234",
        "survey_type": "Cámaras de seguridad (CCTV)",
        "ai_used": False,
    }


def test_intake_endpoint_requires_auth_and_returns_fields(client, admin_token, monkeypatch):
    def boom():
        raise RuntimeError("ollama caído")

    monkeypatch.setattr(intake, "get_client", boom)
    body = {"text": "Ana Reyes 829 555 0000 alarma", "survey_types": TYPES}
    assert client.post("/api/ai/intake-parse", json=body).status_code in (401, 403)

    resp = client.post("/api/ai/intake-parse", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone"] == "829-555-0000"
    assert data["survey_type"] == "Alarma"
    assert data["name"] == "Ana Reyes"
    assert data["ai_used"] is False


def test_project_survey_type_roundtrip(client, admin_token):
    headers = auth_headers(admin_token)
    c = client.post("/api/clients", json={"name": "Cliente Tipo"}, headers=headers).json()
    p = client.post(
        "/api/projects", json={"client_id": c["id"], "survey_type": "Alarma"}, headers=headers
    ).json()
    assert p["survey_type"] == "Alarma"
    updated = client.put(f"/api/projects/{p['id']}", json={"survey_type": "Control de acceso"}, headers=headers)
    assert updated.json()["survey_type"] == "Control de acceso"
    assert client.get(f"/api/projects/{p['id']}", headers=headers).json()["survey_type"] == "Control de acceso"
