from io import BytesIO
from pathlib import Path

from PIL import Image

import pytest

from app.core.config import get_settings
from tests.conftest import auth_headers, make_project, seed_ncf_sequence


@pytest.fixture(autouse=True)
def _no_env_logo(monkeypatch):
    # Las pruebas no deben depender del logo que el desarrollador tenga en su .env.
    monkeypatch.setattr(get_settings(), "company_logo_path", "")


def _logo_png(width=400, height=400, box=(150, 170, 250, 230)) -> bytes:
    """Cuadro blanco con 'tinta' solo en una zona: igual que un logo con mucho aire alrededor."""
    image = Image.new("RGB", (width, height), "white")
    for x in range(box[0], box[2]):
        for y in range(box[1], box[3]):
            image.putpixel((x, y), (10, 10, 10))
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _upload(client, token, data, content_type="image/png"):
    return client.post(
        "/api/company/logo", files={"file": ("logo.png", data, content_type)}, headers=auth_headers(token)
    )


def test_company_falls_back_to_env_until_edited(client, admin_token, monkeypatch):
    monkeypatch.setattr(get_settings(), "company_name", "Nombre del .env")
    monkeypatch.setattr(get_settings(), "company_phone", "809-000-0000")
    headers = auth_headers(admin_token)

    before = client.get("/api/company", headers=headers).json()
    assert before["name"] == "Nombre del .env"
    assert before["has_logo"] is False

    res = client.put("/api/company", json={"name": "Multitec", "tagline": "Servicios de calidad"}, headers=headers)
    assert res.status_code == 200, res.text
    after = res.json()
    assert after["name"] == "Multitec"
    assert after["tagline"] == "Servicios de calidad"
    assert after["phone"] == "809-000-0000"  # lo que no se editó sigue saliendo del .env

    # Vaciar un campo lo devuelve al valor del .env.
    reset = client.put("/api/company", json={"name": "  "}, headers=headers).json()
    assert reset["name"] == "Nombre del .env"


def test_only_admin_can_edit_company(client, admin_token, oficina_token):
    assert client.get("/api/company", headers=auth_headers(oficina_token)).status_code == 200
    assert client.put("/api/company", json={"name": "X"}, headers=auth_headers(oficina_token)).status_code == 403
    assert _upload(client, oficina_token, _logo_png()).status_code == 403


def test_logo_upload_trims_white_margin_and_can_be_replaced_and_removed(client, admin_token):
    from app.services.company import get_company
    from app.db.session import SessionLocal

    res = _upload(client, admin_token, _logo_png())
    assert res.status_code == 200, res.text
    assert res.json()["has_logo"] is True

    served = client.get("/api/company/logo", headers=auth_headers(admin_token))
    assert served.status_code == 200
    image = Image.open(BytesIO(served.content))
    assert image.width < 150 and image.height < 100  # el recuadro de 100x60 más un pequeño margen, no 400x400

    with SessionLocal(company_id=1) as db:
        first_path = get_company(db).logo_path
    assert Path(first_path).is_file()

    assert _upload(client, admin_token, _logo_png(box=(50, 50, 200, 120))).status_code == 200
    assert not Path(first_path).exists()  # el logo anterior se borra del disco

    removed = client.delete("/api/company/logo", headers=auth_headers(admin_token))
    assert removed.status_code == 200
    assert removed.json()["has_logo"] is False
    assert client.get("/api/company/logo", headers=auth_headers(admin_token)).status_code == 404


def test_logo_rejects_non_images_and_blank_images(client, admin_token):
    fake = _upload(client, admin_token, b"<html>no soy una imagen</html>")
    assert fake.status_code == 400

    blank = Image.new("RGB", (100, 100), "white")
    out = BytesIO()
    blank.save(out, format="PNG")
    assert _upload(client, admin_token, out.getvalue()).status_code == 400

    wrong_type = _upload(client, admin_token, _logo_png(), content_type="text/html")
    assert wrong_type.status_code == 400


def test_invoice_pdf_uses_company_profile_and_logo(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    client.put(
        "/api/company",
        json={"name": "Multitec", "bank_info": "Banco Popular 123-456", "invoice_notes": "Gracias por su preferencia."},
        headers=headers,
    )
    assert _upload(client, admin_token, _logo_png()).status_code == 200

    project = make_project(client, headers)
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara & domo <4MP>", "quantity": 2, "unit_price": 500}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()

    pdf = client.get(f"/api/invoices/{invoice['id']}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"
    assert b"/Subtype /Image" in pdf.content  # el logo quedó dentro del PDF


def test_longest_total_label_fits_in_its_column():
    """'TOTAL DEL SERVICIO' (negrita, 11 pt) se cortaba en la barra del total: la columna de la
    etiqueta tiene que medir más que el texto más su relleno."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    from app.services.pdf import CONTENT_WIDTH

    label_width = stringWidth("TOTAL DEL SERVICIO", "Helvetica-Bold", 11)
    label_column = 0.31 * CONTENT_WIDTH
    assert label_width + 8 <= label_column  # 8 pt de relleno derecho
