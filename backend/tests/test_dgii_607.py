import csv
import io
from datetime import date

from tests.conftest import auth_headers, seed_ncf_sequence


def _issue_invoice(client, headers, client_rnc=None, client_name="Cliente 607"):
    client_resp = client.post(
        "/api/clients", json={"name": client_name, "rnc": client_rnc}, headers=headers
    ).json()
    project = client.post("/api/projects", json={"client_id": client_resp["id"]}, headers=headers).json()
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara IP", "quantity": 1, "unit_price": 100}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    return client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()


def _parse_csv(resp):
    text = resp.content.decode("utf-8").lstrip("﻿")
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], rows[1:]


def test_dgii_607_includes_invoices_from_the_period(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B01")
    seed_ncf_sequence(db_session, ncf_type="B02")

    invoice = _issue_invoice(client, headers, client_rnc="130000001", client_name="Empresa con RNC")

    today = date.today()
    resp = client.get(
        "/api/reports/dgii-607", params={"year": today.year, "month": today.month}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "607_" in resp.headers["content-disposition"]

    header, rows = _parse_csv(resp)
    assert header[0] == "RNC/Cédula Comprador"
    assert len(rows) == 1
    row = rows[0]
    assert row[0] == "130000001"  # RNC comprador
    assert row[1] == "1"  # tipo identificación: RNC (9 dígitos)
    assert row[2] == invoice["ncf"]
    assert row[4] == "01"  # tipo de ingreso: operaciones
    assert row[5] == today.strftime("%Y%m%d")
    assert row[7] == "100.0"  # monto facturado
    assert row[8] == "18.0"  # ITBIS facturado


def test_dgii_607_marks_consumer_without_rnc_as_unidentified(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    _issue_invoice(client, headers, client_rnc=None, client_name="Consumidor final")

    today = date.today()
    resp = client.get(
        "/api/reports/dgii-607", params={"year": today.year, "month": today.month}, headers=headers
    )
    _, rows = _parse_csv(resp)
    assert len(rows) == 1
    assert rows[0][0] == ""  # sin RNC
    assert rows[0][1] == "3"  # tipo identificación: no identificado


def test_dgii_607_excludes_invoices_outside_period(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    _issue_invoice(client, headers)

    resp = client.get("/api/reports/dgii-607", params={"year": 2020, "month": 1}, headers=headers)
    _, rows = _parse_csv(resp)
    assert rows == []


def test_dgii_607_rejects_invalid_month(client, admin_token):
    resp = client.get(
        "/api/reports/dgii-607", params={"year": 2026, "month": 13}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 400


def test_dgii_607_forbidden_for_tecnico(client, tecnico_token):
    resp = client.get(
        "/api/reports/dgii-607", params={"year": 2026, "month": 1}, headers=auth_headers(tecnico_token)
    )
    assert resp.status_code == 403
