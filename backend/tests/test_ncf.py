from datetime import date, timedelta

from app.models.invoice import Invoice
from tests.conftest import auth_headers, make_project, seed_ncf_sequence


def _approved_quote(client, headers, project):
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara IP", "quantity": 2, "unit_price": 100}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    return quote


def _pre_invoice(client, headers, project):
    quote = _approved_quote(client, headers, project)
    return client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()


def test_admin_only_can_manage_ncf_sequences(client, admin_token, oficina_token):
    admin_headers = auth_headers(admin_token)
    oficina_headers = auth_headers(oficina_token)

    forbidden = client.post(
        "/api/ncf-sequences",
        json={
            "ncf_type": "B01",
            "description": "Autorización DGII",
            "range_start": 1,
            "range_end": 100,
            "expires_at": str(date.today() + timedelta(days=365)),
        },
        headers=oficina_headers,
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/ncf-sequences",
        json={
            "ncf_type": "B01",
            "description": "Autorización DGII",
            "range_start": 1,
            "range_end": 100,
            "expires_at": str(date.today() + timedelta(days=365)),
        },
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert created.json()["next_number"] == 1
    assert created.json()["active"] is True

    listed = client.get("/api/ncf-sequences", headers=admin_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    forbidden_list = client.get("/api/ncf-sequences", headers=oficina_headers)
    assert forbidden_list.status_code == 403

    deactivated = client.put(
        f"/api/ncf-sequences/{created.json()['id']}", json={"active": False}, headers=admin_headers
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False


def test_convert_to_invoice_defaults_ncf_type_from_client_rnc(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B01")
    seed_ncf_sequence(db_session, ncf_type="B02")

    with_rnc = client.post("/api/clients", json={"name": "Empresa SRL", "rnc": "130000001"}, headers=headers).json()
    project_with_rnc = client.post("/api/projects", json={"client_id": with_rnc["id"]}, headers=headers).json()
    pre_invoice = _pre_invoice(client, headers, project_with_rnc)
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert invoice.status_code == 201
    assert invoice.json()["ncf_type"] == "B01"
    assert invoice.json()["ncf"] == "B0100000001"

    project_no_rnc = make_project(client, headers, client_name="Consumidor final")
    pre_invoice2 = _pre_invoice(client, headers, project_no_rnc)
    invoice2 = client.post(f"/api/pre-invoices/{pre_invoice2['id']}/convert-to-invoice", headers=headers)
    assert invoice2.status_code == 201
    assert invoice2.json()["ncf_type"] == "B02"
    assert invoice2.json()["ncf"] == "B0200000001"


def test_convert_to_invoice_allows_explicit_ncf_type_override(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B14")

    project = make_project(client, headers)
    pre_invoice = _pre_invoice(client, headers, project)
    invoice = client.post(
        f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice",
        json={"ncf_type": "B14"},
        headers=headers,
    )
    assert invoice.status_code == 201
    assert invoice.json()["ncf_type"] == "B14"


def test_convert_to_invoice_fails_without_active_sequence(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    pre_invoice = _pre_invoice(client, headers, project)

    resp = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert resp.status_code == 400
    assert "secuencia NCF" in resp.json()["detail"]


def test_convert_to_invoice_fails_with_expired_sequence(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02", expires_at=date.today() - timedelta(days=1))

    project = make_project(client, headers)
    pre_invoice = _pre_invoice(client, headers, project)
    resp = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert resp.status_code == 400


def test_convert_to_invoice_fails_with_inactive_sequence(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02", active=False)

    project = make_project(client, headers)
    pre_invoice = _pre_invoice(client, headers, project)
    resp = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert resp.status_code == 400


def test_ncf_sequence_exhaustion(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02", range_start=1, range_end=1)

    project = make_project(client, headers)
    pre_invoice = _pre_invoice(client, headers, project)
    first = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert first.status_code == 201
    assert first.json()["ncf"] == "B0200000001"

    project2 = make_project(client, headers, client_name="Otro cliente")
    pre_invoice2 = _pre_invoice(client, headers, project2)
    second = client.post(f"/api/pre-invoices/{pre_invoice2['id']}/convert-to-invoice", headers=headers)
    assert second.status_code == 400


def test_overlapping_active_sequences_pick_deterministically(client, admin_token, db_session):
    """Dos secuencias B02 activas con el mismo rango y vencimiento (error de captura del
    admin) no deben resolverse al azar — siempre gana la más antigua (menor id), así que
    conversiones repetidas nunca chocan entre sí mientras esa siga vigente."""
    headers = auth_headers(admin_token)
    seq_a = seed_ncf_sequence(db_session, ncf_type="B02")
    seed_ncf_sequence(db_session, ncf_type="B02")  # rango idéntico, vencimiento idéntico

    project = make_project(client, headers)
    pre_invoice = _pre_invoice(client, headers, project)
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert invoice.status_code == 201
    assert invoice.json()["ncf"] == "B0200000001"

    db_session.refresh(seq_a)
    assert seq_a.next_number == 2  # se consumió de la secuencia con menor id, no de la otra


def test_ncf_collision_returns_clean_400_not_500(client, admin_token, db_session):
    """Si por algún motivo ya existe una factura con el NCF que le tocaría a la siguiente
    (p. ej. secuencias solapadas creadas manualmente), el conflicto de unicidad en BD debe
    traducirse en un 400 explicable, no un 500 genérico."""
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")

    project = make_project(client, headers)
    other_pre_invoice = _pre_invoice(client, headers, project)
    db_session.add(
        Invoice(
            code="FAC-PRECOLISION",
            project_id=project["id"],
            pre_invoice_id=other_pre_invoice["id"],
            ncf="B0200000001",
            ncf_type="B02",
            subtotal=0,
            itbis=0,
            total=0,
        )
    )
    db_session.commit()

    pre_invoice = _pre_invoice(client, headers, project)
    resp = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert resp.status_code == 400
    assert "ya fue usado" in resp.json()["detail"]
