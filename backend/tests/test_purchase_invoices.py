import csv
import io
from datetime import date

from tests.conftest import auth_headers


def _supplier(client, headers, rnc="101000001"):
    return client.post("/api/suppliers", json={"name": "Proveedor Uno", "rnc": rnc}, headers=headers).json()


def _payload(supplier_id, **overrides):
    data = {
        "supplier_id": supplier_id,
        "ncf": "B0100000001",
        "invoice_date": date.today().isoformat(),
        "services_amount": 100,
        "goods_amount": 400,
        "itbis_invoiced": 90,
    }
    data.update(overrides)
    return data


def _parse_csv(resp):
    text = resp.content.decode("utf-8").lstrip("﻿")
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], rows[1:]


def test_crud_flow(client, admin_token):
    headers = auth_headers(admin_token)
    supplier = _supplier(client, headers)

    created = client.post("/api/purchase-invoices", json=_payload(supplier["id"]), headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["supplier_name"] == "Proveedor Uno"
    assert body["expense_type"] == "09"

    listed = client.get("/api/purchase-invoices", headers=headers).json()
    assert [i["id"] for i in listed] == [body["id"]]

    updated = client.put(
        f"/api/purchase-invoices/{body['id']}",
        json=_payload(supplier["id"], itbis_invoiced=18, payment_type="02"),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["payment_type"] == "02"

    assert client.delete(f"/api/purchase-invoices/{body['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/purchase-invoices/{body['id']}", headers=headers).status_code == 404


def test_rejects_duplicate_ncf_for_same_supplier(client, admin_token):
    headers = auth_headers(admin_token)
    supplier = _supplier(client, headers)
    assert client.post("/api/purchase-invoices", json=_payload(supplier["id"]), headers=headers).status_code == 201
    dup = client.post("/api/purchase-invoices", json=_payload(supplier["id"]), headers=headers)
    assert dup.status_code == 409


def test_validates_codes_and_supplier(client, admin_token):
    headers = auth_headers(admin_token)
    supplier = _supplier(client, headers)
    bad_type = client.post(
        "/api/purchase-invoices", json=_payload(supplier["id"], expense_type="99"), headers=headers
    )
    assert bad_type.status_code == 422
    missing = client.post("/api/purchase-invoices", json=_payload(9999), headers=headers)
    assert missing.status_code == 404


def test_requires_auth(client):
    assert client.get("/api/purchase-invoices").status_code in (401, 403)


def test_dgii_606_export(client, admin_token):
    headers = auth_headers(admin_token)
    supplier = _supplier(client, headers, rnc="101000001")
    client.post("/api/purchase-invoices", json=_payload(supplier["id"], itbis_withheld=5), headers=headers)
    client.post(
        "/api/purchase-invoices",
        json=_payload(supplier["id"], ncf="B0100000002", invoice_date="2020-01-15"),
        headers=headers,
    )

    today = date.today()
    resp = client.get("/api/reports/dgii-606", params={"year": today.year, "month": today.month}, headers=headers)
    assert resp.status_code == 200
    assert "606_" in resp.headers["content-disposition"]

    header, rows = _parse_csv(resp)
    assert header[0] == "RNC/Cédula Proveedor"
    assert len(rows) == 1  # la de 2020 queda fuera del período
    row = rows[0]
    assert row[0] == "101000001"
    assert row[1] == "1"
    assert row[3] == "B0100000001"
    assert row[5] == today.strftime("%Y%m%d")
    assert row[7] == "100.0" and row[8] == "400.0" and row[9] == "500.0"
    assert row[10] == "90.0" and row[11] == "5.0"
    assert row[22] == "04"


def test_dgii_606_rejects_invalid_month(client, admin_token):
    resp = client.get("/api/reports/dgii-606", params={"year": 2026, "month": 13}, headers=auth_headers(admin_token))
    assert resp.status_code == 400
