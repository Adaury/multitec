import csv
import io
from datetime import date

from app.core.config import get_settings
from tests.conftest import auth_headers, seed_ncf_sequence
from tests.test_dgii_607 import _issue_invoice, _parse_csv


def _period():
    today = date.today()
    return {"year": today.year, "month": today.month}


def test_void_requires_admin_and_a_valid_reason(client, admin_token, oficina_token, db_session):
    seed_ncf_sequence(db_session, ncf_type="B02")
    invoice = _issue_invoice(client, auth_headers(admin_token), client_name="Anulable")

    denied = client.post(
        f"/api/invoices/{invoice['id']}/void", json={"reason_code": "04"}, headers=auth_headers(oficina_token)
    )
    bad = client.post(
        f"/api/invoices/{invoice['id']}/void", json={"reason_code": "99"}, headers=auth_headers(admin_token)
    )

    assert denied.status_code == 403
    assert bad.status_code == 422


def test_voided_invoice_leaves_the_607_and_lands_in_the_608(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    invoice = _issue_invoice(client, headers, client_name="Cliente anulado")

    resp = client.post(
        f"/api/invoices/{invoice['id']}/void", json={"reason_code": "04", "note": "RNC mal digitado"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["void_reason"] == "04"
    assert resp.json()["voided_at"] is not None

    r607 = client.get("/api/reports/dgii-607", params=_period(), headers=headers)
    _, rows607 = _parse_csv(r607)
    assert rows607 == []

    r608 = client.get("/api/reports/dgii-608", params=_period(), headers=headers)
    header, rows608 = _parse_csv(r608)
    assert header[0] == "Número de Comprobante Fiscal"
    assert rows608[0][0] == invoice["ncf"]
    assert rows608[0][1] == date.today().strftime("%Y%m%d")
    assert rows608[0][2] == "04"


def test_a_voided_invoice_cannot_be_voided_twice(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    invoice = _issue_invoice(client, headers, client_name="Doble anulación")

    first = client.post(f"/api/invoices/{invoice['id']}/void", json={"reason_code": "01"}, headers=headers)
    second = client.post(f"/api/invoices/{invoice['id']}/void", json={"reason_code": "01"}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 400


def test_dashboard_and_history_ignore_voided_invoices(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    invoice = _issue_invoice(client, headers, client_name="Fuera del dashboard")
    before = client.get("/api/reports/dashboard", headers=headers).json()["monthly_invoicing"][-1]["total"]

    client.post(f"/api/invoices/{invoice['id']}/void", json={"reason_code": "06"}, headers=headers)

    after = client.get("/api/reports/dashboard", headers=headers).json()["monthly_invoicing"][-1]["total"]
    history = client.get(f"/api/invoices/{invoice['id']}/history", headers=headers).json()
    assert after == before - 118.0
    assert history[-1]["action"] == "anulada"


def test_txt_for_the_dgii_has_a_header_record_and_no_column_titles(client, admin_token, db_session, monkeypatch):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B01")
    invoice = _issue_invoice(client, headers, client_rnc="130000001", client_name="Empresa TXT")
    monkeypatch.setattr(get_settings(), "company_rnc", "1-31-00000-1")

    resp = client.get("/api/reports/dgii-607", params={**_period(), "format": "txt"}, headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert f'DGII_F_607_131000001_{date.today():%Y%m}.TXT' in resp.headers["content-disposition"]
    lines = resp.content.decode("utf-8").splitlines()
    assert lines[0] == f"607|131000001|{date.today():%Y%m}|1"
    fields = lines[1].split("|")
    assert fields[0] == "130000001"
    assert fields[2] == invoice["ncf"]
    assert fields[7] == "100.00"
    assert len(fields) == 23


def test_txt_without_company_rnc_explains_what_is_missing(client, admin_token, monkeypatch):
    monkeypatch.setattr(get_settings(), "company_rnc", "")

    resp = client.get(
        "/api/reports/dgii-608", params={**_period(), "format": "txt"}, headers=auth_headers(admin_token)
    )

    assert resp.status_code == 400
    assert "COMPANY_RNC" in resp.json()["detail"]


def test_607_places_the_income_tax_retention_in_the_official_column(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B01")
    invoice = _issue_invoice(client, headers, client_rnc="130000002", client_name="Con retención")
    client.put(
        f"/api/invoices/{invoice['id']}/payment",
        json={
            "payment_method": "cheque_transferencia",
            "itbis_withheld": 18,
            "isr_withheld": 10,
            "retention_date": date.today().isoformat(),
        },
        headers=headers,
    )

    resp = client.get("/api/reports/dgii-607", params=_period(), headers=headers)
    header, rows = _parse_csv(resp)

    assert header[11] == "Retención Renta por Terceros"
    assert header[12] == "ISR Percibido"
    assert rows[0][9] == "18.0"  # ITBIS retenido por terceros (col. 10)
    assert rows[0][11] == "10.0"  # retención de renta (col. 12)
    assert rows[0][12] == ""  # ISR percibido (col. 13) no se toca
