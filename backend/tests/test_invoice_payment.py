from datetime import date

from tests.conftest import auth_headers, seed_ncf_sequence
from tests.test_dgii_607 import _issue_invoice, _parse_csv


def _row_607(client, headers):
    today = date.today()
    resp = client.get("/api/reports/dgii-607", params={"year": today.year, "month": today.month}, headers=headers)
    assert resp.status_code == 200
    header, rows = _parse_csv(resp)
    return header, rows


def test_payment_and_retentions_fill_the_607_columns(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B01")
    invoice = _issue_invoice(client, headers, client_rnc="130000001")  # 100 + ITBIS 18 = 118
    assert invoice["payment_method"] is None
    assert invoice["itbis_withheld"] == 0

    # Antes de registrar nada, las columnas salen vacías (comportamiento anterior).
    _, rows = _row_607(client, headers)
    assert rows[0][6] == "" and rows[0][9] == "" and rows[0][12] == "" and rows[0][16:] == [""] * 7

    today = date.today().isoformat()
    resp = client.put(
        f"/api/invoices/{invoice['id']}/payment",
        json={"payment_method": "tarjeta", "itbis_withheld": 9, "isr_withheld": 5, "retention_date": today},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["payment_method"] == "tarjeta"
    assert body["itbis_withheld"] == 9 and body["isr_withheld"] == 5

    header, rows = _row_607(client, headers)
    row = dict(zip(header, rows[0]))
    assert row["Tarjeta Débito/Crédito"] == "118.0"  # total cobrado
    assert row["Efectivo"] == "" and row["Venta a Crédito"] == ""
    assert row["ITBIS Retenido"] == "9.0"
    assert row["Retención Renta por Terceros"] == "5.0"
    assert row["Fecha Retención"] == date.today().strftime("%Y%m%d")

    # Cada forma de pago cae en su propia columna.
    for method, column in [
        ("efectivo", "Efectivo"),
        ("cheque_transferencia", "Cheque/Transferencia/Depósito"),
        ("credito", "Venta a Crédito"),
        ("bonos", "Bonos o Certificados de Regalo"),
        ("permuta", "Permuta"),
        ("otras", "Otras Formas de Venta"),
    ]:
        client.put(f"/api/invoices/{invoice['id']}/payment", json={"payment_method": method}, headers=headers)
        header, rows = _row_607(client, headers)
        row = dict(zip(header, rows[0]))
        assert row[column] == "118.0", method
        assert row["ITBIS Retenido"] == ""  # sin retención, aunque antes la hubiera

    # Queda en el historial de la factura.
    history = client.get(f"/api/invoices/{invoice['id']}/history", headers=headers).json()
    assert any(h["action"] == "pago actualizado" for h in history)


def test_payment_validation(client, admin_token, tecnico_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    invoice = _issue_invoice(client, headers)
    url = f"/api/invoices/{invoice['id']}/payment"
    today = date.today().isoformat()

    # Retención sin fecha.
    assert client.put(url, json={"itbis_withheld": 5}, headers=headers).status_code == 400
    # Retener más ITBIS del que tiene la factura (18).
    assert (
        client.put(url, json={"itbis_withheld": 19, "retention_date": today}, headers=headers).status_code == 400
    )
    # Retener más renta que el subtotal (100).
    assert client.put(url, json={"isr_withheld": 101, "retention_date": today}, headers=headers).status_code == 400
    # Forma de pago inventada, y valores negativos.
    assert client.put(url, json={"payment_method": "bitcoin"}, headers=headers).status_code == 422
    assert client.put(url, json={"itbis_withheld": -1}, headers=headers).status_code == 422
    # Factura inexistente.
    assert client.put("/api/invoices/99999/payment", json={}, headers=headers).status_code == 404
    # El técnico no maneja facturación.
    assert client.put(url, json={"payment_method": "efectivo"}, headers=auth_headers(tecnico_token)).status_code == 403
