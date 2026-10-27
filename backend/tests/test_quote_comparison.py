import io
from unittest.mock import patch

from reportlab.pdfgen import canvas

from app.services.quote_compare import ExtractedQuote, similarity
from tests.conftest import auth_headers, make_category, make_project
from tests.test_survey_markers_and_annex import _upload_real_photo


def _pdf_with_text(lines):
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    y = 800
    for line in lines:
        pdf.drawString(50, y, line)
        y -= 20
    pdf.save()
    return buf.getvalue()


def _our_quote(client, headers, project_id):
    category = make_category(client, headers, name="Cámaras de seguridad (CCTV)", code_prefix="CAM")
    cam = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "Cámara domo IP 4MP", "unit": "unidad", "price": 4500},
        headers=headers,
    ).json()
    quote = client.post(
        f"/api/projects/{project_id}/quotes",
        json={
            "items": [
                {"product_id": cam["id"], "description": cam["name"], "quantity": 4},
                {"description": "NVR 8 canales con disco 2TB", "quantity": 1, "unit_price": 18000},
                {"description": "Cable UTP cat6 rollo", "quantity": 2, "unit_price": 4500},
            ]
        },
        headers=headers,
    )
    assert quote.status_code == 201, quote.text
    return quote.json()


EXTERNAL = ExtractedQuote(
    items=[
        {"description": "Camara domo IP 4MP Hikvision", "quantity": 6, "unit_price": 4200},
        {"description": "NVR 8 canales disco 2TB", "quantity": 1, "unit_price": 18000},
        {"description": "Router WiFi 6", "quantity": 1, "unit_price": 3500},
    ],
    total=60000,
)
SOME_TEXT = "Cotización de ejemplo con varias líneas de productos"


def test_similarity_ignores_accents_and_filler_words():
    assert similarity("Cámara domo IP 4MP", "Camara domo IP 4MP Hikvision") > 0.5
    assert similarity("Cámara domo IP 4MP", "Cable UTP cat6") < 0.2


def test_compare_uploaded_text_against_our_quote_and_the_survey_points(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    quote = _our_quote(client, h, project["id"])
    photo = _upload_real_photo(client, h, project["id"])
    marked = [{"x": 0.1 * (i + 1), "y": 0.5, "label": f"Cámara {i + 1}", "kind": "camara"} for i in range(5)]
    client.put(f"/api/projects/{project['id']}/survey/assets/{photo['id']}/markers", json={"markers": marked}, headers=h)

    with patch("app.api.routers.comparisons.read_items", return_value=EXTERNAL):
        resp = client.post(
            f"/api/projects/{project['id']}/comparisons",
            data={"label": "Competidor X", "text": SOME_TEXT},
            headers=h,
        )
    assert resp.status_code == 201, resp.text
    out = resp.json()
    assert out["label"] == "Competidor X" and len(out["items"]) == 3

    by_desc = {m["external"]["description"]: m for m in out["matched"]}
    camera = by_desc["Camara domo IP 4MP Hikvision"]
    assert camera["same_quantity"] is False and camera["price"] == "mas_barato" and camera["price_diff_pct"] < 0
    nvr = by_desc["NVR 8 canales disco 2TB"]
    assert nvr["status"] == "igual"
    assert [i["description"] for i in out["only_external"]] == ["Router WiFi 6"]
    assert [i["description"] for i in out["only_ours"]] == ["Cable UTP cat6 rollo"]

    # El levantamiento marcó 5 cámaras: la ajena trae 6 (sobra una) y la propia 4 (falta una)
    cams = next(c for c in out["coverage"] if c["kind"] == "camara")
    assert (cams["marked"], cams["external"], cams["ours"]) == (5, 6, 4)
    assert cams["external_status"] == "sobra" and cams["ours_status"] == "falta"
    assert out["totals"]["our_code"] == quote["code"] and out["totals"]["external_total"] == 60000


def test_upload_pdf_reads_its_text_and_keeps_the_file(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    pdf = _pdf_with_text(["COTIZACION 123", "Camara domo IP 4MP  6 x 4200.00", "NVR 8 canales  1 x 18000.00"])
    seen = {}

    def fake_read(text):
        seen["text"] = text
        return EXTERNAL

    with patch("app.api.routers.comparisons.read_items", side_effect=fake_read):
        resp = client.post(
            f"/api/projects/{project['id']}/comparisons",
            data={"label": "Proveedor Y"},
            files={"file": ("cot.pdf", io.BytesIO(pdf), "application/pdf")},
            headers=h,
        )
    assert resp.status_code == 201, resp.text
    assert "Camara domo IP 4MP" in seen["text"]  # el texto salió del PDF de verdad
    assert resp.json()["filename"] == "cot.pdf" and resp.json()["file_path"].endswith(".pdf")


def test_upload_rejects_bad_files_and_empty_requests(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    url = f"/api/projects/{project['id']}/comparisons"
    fake_pdf = client.post(url, data={"label": "x"}, files={"file": ("a.pdf", io.BytesIO(b"hola"), "application/pdf")}, headers=h)
    assert fake_pdf.status_code == 400 and "no es un PDF" in fake_pdf.json()["detail"]
    other = client.post(url, data={"label": "x"}, files={"file": ("a.txt", io.BytesIO(b"hola"), "text/plain")}, headers=h)
    assert other.status_code == 400 and "PDF o una foto" in other.json()["detail"]
    scanned = client.post(
        url, data={"label": "x"}, files={"file": ("a.pdf", io.BytesIO(_pdf_with_text([])), "application/pdf")}, headers=h
    )
    assert scanned.status_code == 400 and "escaneado" in scanned.json()["detail"]
    assert client.post(url, data={"label": "x"}, headers=h).status_code == 400
    with patch("app.api.routers.comparisons.read_items", return_value=ExtractedQuote(items=[])):
        empty = client.post(url, data={"label": "x", "text": SOME_TEXT}, headers=h)
    assert empty.status_code == 400 and "No encontré líneas" in empty.json()["detail"]


def test_office_can_fix_the_lines_and_the_result_updates(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    _our_quote(client, h, project["id"])
    with patch("app.api.routers.comparisons.read_items", return_value=EXTERNAL):
        created = client.post(
            f"/api/projects/{project['id']}/comparisons",
            data={"label": "Competidor X", "text": SOME_TEXT},
            headers=h,
        ).json()
    url = f"/api/projects/{project['id']}/comparisons/{created['id']}"
    fixed = client.put(
        url,
        json={"items": [{"description": "Cámara domo IP 4MP", "quantity": 4, "unit_price": 4500}], "label": "Competidor X (corregido)"},
        headers=h,
    ).json()
    assert fixed["label"] == "Competidor X (corregido)"
    assert fixed["matched"][0]["status"] == "igual" and fixed["only_external"] == []
    assert [c["id"] for c in client.get(f"/api/projects/{project['id']}/comparisons", headers=h).json()] == [created["id"]]
    assert client.delete(url, headers=h).status_code == 204
    assert client.get(url, headers=h).status_code == 404


def test_technician_cannot_see_comparisons(client, admin_token, tecnico_token):
    project = make_project(client, auth_headers(admin_token))
    url = f"/api/projects/{project['id']}/comparisons"
    assert client.get(url, headers=auth_headers(tecnico_token)).status_code == 403
