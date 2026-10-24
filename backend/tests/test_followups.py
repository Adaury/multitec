from datetime import timedelta

from app.core.timeutil import today_dr
from app.models.invoice import Invoice
from app.models.quote import Quote
from app.services.followups import quote_message, whatsapp_link
from tests.conftest import auth_headers, make_project, seed_ncf_sequence


def _issue_invoice(client, db_session, headers, phone="809-555-0101"):
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    if phone:
        updated = client.put(
            f"/api/clients/{project['client_id']}", json={"name": "Cliente de prueba", "phone": phone}, headers=headers
        )
        assert updated.status_code == 200, updated.text
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara", "quantity": 1, "unit_price": 1000}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre['id']}/convert-to-invoice", headers=headers).json()
    return project, quote, invoice


def _age(db_session, model, row_id, days):
    from datetime import datetime, timezone

    row = db_session.get(model, row_id)
    row.created_at = datetime.now(timezone.utc) - timedelta(days=days)
    db_session.commit()


def test_unpaid_invoice_is_listed_with_message_and_whatsapp_link(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    _, _, invoice = _issue_invoice(client, db_session, headers)

    data = client.get("/api/followups", headers=headers).json()

    assert [r["code"] for r in data["receivables"]] == [invoice["code"]]
    row = data["receivables"][0]
    assert row["overdue"] is False
    assert row["whatsapp_url"].startswith("https://wa.me/18095550101?text=")
    assert invoice["code"] in row["message"] and "RD$" in row["message"]
    assert data["receivables_total"] == invoice["total"]
    assert data["overdue_count"] == 0


def test_overdue_invoice_is_flagged_and_sorted_first(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    _, _, recent = _issue_invoice(client, db_session, headers)
    _, _, old = _issue_invoice(client, db_session, headers)
    _age(db_session, Invoice, old["id"], 20)

    data = client.get("/api/followups", headers=headers).json()

    assert [r["code"] for r in data["receivables"]] == [old["code"], recent["code"]]
    assert data["receivables"][0]["overdue"] is True
    assert data["receivables"][0]["days_overdue"] >= 12
    assert "venció" in data["receivables"][0]["message"]
    assert data["overdue_count"] == 1
    assert data["overdue_total"] == old["total"]


def test_marking_paid_removes_it_and_can_be_undone(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    _, _, invoice = _issue_invoice(client, db_session, headers)

    paid = client.put(f"/api/invoices/{invoice['id']}/paid", json={"paid": True}, headers=headers)
    assert paid.status_code == 200, paid.text
    assert paid.json()["paid_at"] == today_dr().isoformat()
    assert client.get("/api/followups", headers=headers).json()["receivables"] == []

    undone = client.put(f"/api/invoices/{invoice['id']}/paid", json={"paid": False}, headers=headers)
    assert undone.json()["paid_at"] is None
    assert len(client.get("/api/followups", headers=headers).json()["receivables"]) == 1


def test_cannot_mark_paid_in_the_future_or_a_voided_invoice(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    _, _, invoice = _issue_invoice(client, db_session, headers)

    tomorrow = (today_dr() + timedelta(days=1)).isoformat()
    assert client.put(f"/api/invoices/{invoice['id']}/paid", json={"paid_at": tomorrow}, headers=headers).status_code == 400

    voided = client.post(f"/api/invoices/{invoice['id']}/void", json={"reason_code": "04"}, headers=headers)
    assert voided.status_code == 200, voided.text
    assert client.put(f"/api/invoices/{invoice['id']}/paid", json={}, headers=headers).status_code == 400
    assert client.get("/api/followups", headers=headers).json()["receivables"] == []


def test_registering_a_cash_payment_marks_it_paid_but_credit_does_not(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    _, _, cash = _issue_invoice(client, db_session, headers)
    _, _, credit = _issue_invoice(client, db_session, headers)

    client.put(f"/api/invoices/{cash['id']}/payment", json={"payment_method": "efectivo"}, headers=headers)
    client.put(f"/api/invoices/{credit['id']}/payment", json={"payment_method": "credito"}, headers=headers)

    codes = [r["code"] for r in client.get("/api/followups", headers=headers).json()["receivables"]]
    assert codes == [credit["code"]]


def test_quotes_without_answer_appear_after_three_days_only(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara", "quantity": 1, "unit_price": 1000}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()

    assert client.get("/api/followups", headers=headers).json()["quotes"] == []

    _age(db_session, Quote, quote["id"], 4)
    rows = client.get("/api/followups", headers=headers).json()["quotes"]
    assert [r["code"] for r in rows] == [quote["code"]]
    assert rows[0]["stale"] is False

    _age(db_session, Quote, quote["id"], 9)
    assert client.get("/api/followups", headers=headers).json()["quotes"][0]["stale"] is True

    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    assert client.get("/api/followups", headers=headers).json()["quotes"] == []


def test_technician_cannot_see_followups(client, tecnico_token):
    assert client.get("/api/followups", headers=auth_headers(tecnico_token)).status_code == 403


def test_whatsapp_link_only_for_valid_dominican_numbers():
    assert whatsapp_link("829-477-8613", "hola").startswith("https://wa.me/18294778613?text=hola")
    assert whatsapp_link("1 (829) 477-8613", "x").startswith("https://wa.me/18294778613")
    assert whatsapp_link("12345", "x") is None
    assert whatsapp_link(None, "x") is None
    assert "%20" in whatsapp_link("8294778613", "dos palabras")


def test_message_wording():
    from datetime import date

    msg = quote_message("Multitec", "Ana", "COT-000001", 1180, date(2026, 10, 1))
    assert "Multitec" in msg and "COT-000001" in msg and "RD$ 1,180.00" in msg and "01/10/2026" in msg
