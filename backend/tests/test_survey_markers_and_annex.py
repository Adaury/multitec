import io

from PIL import Image

from tests.conftest import auth_headers, make_project


def _png_bytes(width=400, height=300):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (200, 210, 220)).save(buf, format="PNG")
    return buf.getvalue()


def _upload_real_photo(client, headers, project_id):
    resp = client.post(
        f"/api/projects/{project_id}/survey/assets",
        data={"kind": "photo", "description": "Fachada frontal"},
        files={"file": ("fachada.png", io.BytesIO(_png_bytes()), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _quote_for(client, headers, project_id):
    budget = client.post(
        f"/api/projects/{project_id}/budgets",
        json={"items": [{"description": "Cámara IP", "quantity": 2, "unit_price": 100}]},
        headers=headers,
    ).json()
    return client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()


def test_markers_are_numbered_across_the_whole_survey(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    first = _upload_real_photo(client, headers, project["id"])
    second = _upload_real_photo(client, headers, project["id"])

    r1 = client.put(
        f"/api/projects/{project['id']}/survey/assets/{first['id']}/markers",
        json={"markers": [{"x": 0.2, "y": 0.3, "label": "Cámara entrada"}, {"x": 0.7, "y": 0.4, "label": "Cámara patio"}]},
        headers=headers,
    )
    r2 = client.put(
        f"/api/projects/{project['id']}/survey/assets/{second['id']}/markers",
        json={"markers": [{"x": 0.5, "y": 0.5, "label": "NVR"}]},
        headers=headers,
    )

    assert [m["number"] for m in r1.json()["markers"]] == [1, 2]
    assert [m["number"] for m in r2.json()["markers"]] == [3]

    # Quitar un marcador de la primera foto renumera la segunda: sin huecos.
    client.put(
        f"/api/projects/{project['id']}/survey/assets/{first['id']}/markers",
        json={"markers": [{"x": 0.2, "y": 0.3, "label": "Cámara entrada"}]},
        headers=headers,
    )
    survey = client.get(f"/api/projects/{project['id']}/survey", headers=headers).json()
    numbers = {a["id"]: [m["number"] for m in a["markers"]] for a in survey["assets"]}
    assert numbers[first["id"]] == [1]
    assert numbers[second["id"]] == [2]


def test_marker_coordinates_must_be_inside_the_photo(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    photo = _upload_real_photo(client, headers, project["id"])

    resp = client.put(
        f"/api/projects/{project['id']}/survey/assets/{photo['id']}/markers",
        json={"markers": [{"x": 1.4, "y": 0.2, "label": "Fuera"}]},
        headers=headers,
    )

    assert resp.status_code == 422


def test_quote_pdf_with_photo_annex_is_bigger_and_still_a_pdf(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    photo = _upload_real_photo(client, headers, project["id"])
    client.put(
        f"/api/projects/{project['id']}/survey/assets/{photo['id']}/markers",
        json={"markers": [{"x": 0.3, "y": 0.3, "label": "Cámara 4MP"}]},
        headers=headers,
    )
    quote = _quote_for(client, headers, project["id"])

    plain = client.get(f"/api/quotes/{quote['id']}/pdf", headers=headers)
    marked = client.get(f"/api/quotes/{quote['id']}/pdf", params={"photos": "marked"}, headers=headers)

    assert marked.status_code == 200
    assert marked.content.startswith(b"%PDF")
    assert len(marked.content) > len(plain.content)


def test_portal_quote_pdf_and_client_rejection(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    quote = _quote_for(client, headers, project["id"])
    token = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]

    pdf = client.get(f"/api/public/projects/{token}/quotes/{quote['id']}/pdf")
    rejected = client.post(
        f"/api/public/projects/{token}/quotes/{quote['id']}/reject",
        json={"reason": "Muy caro", "signer_name": "María Pérez"},
    )

    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert rejected.status_code == 200
    assert rejected.json()["quotes"][0]["status"] == "no_aprobada"
    history = client.get(f"/api/quotes/{quote['id']}/history", headers=headers).json()
    assert any("Muy caro" in (h["note"] or "") and "María Pérez" in (h["note"] or "") for h in history)

    again = client.post(f"/api/public/projects/{token}/quotes/{quote['id']}/reject", json={})
    assert again.status_code == 400


def test_portal_approval_records_who_signed(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    quote = _quote_for(client, headers, project["id"])
    token = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]

    resp = client.post(
        f"/api/public/projects/{token}/quotes/{quote['id']}/approve", json={"signer_name": "Juan Gómez"}
    )

    assert resp.status_code == 200
    history = client.get(f"/api/quotes/{quote['id']}/history", headers=headers).json()
    assert any("Juan Gómez" in (h["note"] or "") for h in history)


def test_voided_invoices_are_hidden_from_the_portal(client, admin_token, db_session):
    from tests.conftest import seed_ncf_sequence
    from tests.test_dgii_607 import _issue_invoice

    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    invoice = _issue_invoice(client, headers, client_name="Portal con anulada")
    token = client.post(f"/api/projects/{invoice['project_id']}/public-link", headers=headers).json()["token"]
    assert len(client.get(f"/api/public/projects/{token}").json()["invoices"]) == 1

    client.post(f"/api/invoices/{invoice['id']}/void", json={"reason_code": "04"}, headers=headers)

    assert client.get(f"/api/public/projects/{token}").json()["invoices"] == []
