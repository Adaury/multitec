"""Puntos marcados en las fotos → cantidades exactas en la cotización con IA."""

from unittest.mock import patch

from app.services.survey_points import infer_kind, points_context, reconcile_items
from tests.conftest import auth_headers, make_category, make_project
from tests.test_survey_markers_and_annex import _upload_real_photo


def test_infer_kind_from_the_label():
    assert infer_kind("Cámara entrada") == "camara"
    assert infer_kind("camara 3") == "camara"
    assert infer_kind("NVR central") == "grabador"
    assert infer_kind("Switch PoE") == "switch"
    assert infer_kind("Lector de huella") == "acceso"
    assert infer_kind("Algo raro") == "otro"
    assert infer_kind(None) == "otro"


def test_context_block_gives_exact_counts():
    text = points_context({"camara": 6, "grabador": 1})
    assert "EXACTAS" in text and "Cámara: 6" in text and "NVR / DVR: 1" in text
    assert points_context({}) == ""


def test_reconcile_raises_a_single_camera_line_to_the_marked_count():
    items = [
        {"product_id": 1, "description": "Cámara domo IP 4MP", "quantity": 4},
        {"product_id": 2, "description": "Fuente 12V para cámaras", "quantity": 4},
    ]
    result = reconcile_items(items, {"camara": 6}, {1: "Cámaras de seguridad (CCTV)", 2: "Fuentes"})
    assert result.items[0]["quantity"] == 6.0
    assert result.items[1]["quantity"] == 4  # el accesorio no cuenta como cámara ni se toca
    assert "de 4 a 6" in result.warnings[0]


def test_reconcile_warns_instead_of_guessing_when_there_are_several_lines_or_fewer_marked():
    several = [
        {"product_id": 1, "description": "Cámara bullet 2MP", "quantity": 2},
        {"product_id": 2, "description": "Cámara domo 4MP", "quantity": 1},
    ]
    r = reconcile_items(several, {"camara": 5}, {1: "Cámaras", 2: "Cámaras"})
    assert [i["quantity"] for i in r.items] == [2, 1] and "suma 3" in r.warnings[0]

    fewer = [{"product_id": 1, "description": "Cámara domo", "quantity": 8}]
    r = reconcile_items(fewer, {"camara": 6}, {1: "Cámaras"})
    assert r.items[0]["quantity"] == 8 and "confirma que no sobren" in r.warnings[0]

    r = reconcile_items([{"product_id": None, "description": "Rack 6U", "quantity": 1}], {"grabador": 1}, {})
    assert "no trae ese equipo" in r.warnings[0]


def test_marker_kind_is_saved_and_counted_and_drives_the_generated_quote(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    category = make_category(client, headers, name="Cámaras de seguridad (CCTV)", code_prefix="CAM")
    product = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "Cámara domo IP 4MP", "unit": "unidad", "price": 150},
        headers=headers,
    ).json()
    photo = _upload_real_photo(client, headers, project["id"])
    resp = client.put(
        f"/api/projects/{project['id']}/survey/assets/{photo['id']}/markers",
        json={
            "markers": [
                {"x": 0.1, "y": 0.1, "label": "Entrada", "kind": "camara"},
                {"x": 0.2, "y": 0.2, "label": "Patio", "kind": "camara"},
                {"x": 0.3, "y": 0.3, "label": "Cámara garaje"},  # sin tipo: se deduce del nombre
                {"x": 0.4, "y": 0.4, "label": "Punto raro", "kind": "inventado"},  # tipo inválido: se ignora
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert [m["point_kind"] for m in resp.json()["markers"]] == ["camara", "camara", "camara", "otro"]

    # La IA entendió solo 1 cámara; los puntos marcados dicen 3: la cotización sale con 3
    with (
        patch(
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": product["id"], "description": product["name"], "quantity": 1}],
        ),
        patch(
            "app.ai_engine.documents.draft_engineering",
            return_value={
                "recommended_equipment": "x",
                "distribution": "x",
                "conduits": "x",
                "wiring": "x",
                "technical_design": "x",
                "observations": "x",
            },
        ),
        patch("app.api.routers.ai.reindex_project"),
    ):
        out = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)
    assert out.status_code == 200, out.text
    body = out.json()
    camera_line = next(i for i in body["quote"]["items"] if i["product_id"] == product["id"])
    assert camera_line["quantity"] == 3
    assert any("de 1 a 3" in w for w in body["warnings"])
