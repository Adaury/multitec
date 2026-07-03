from tests.conftest import auth_headers, create_user, make_project, seed_ncf_sequence


def _capture_emails(monkeypatch):
    sent = []

    def fake_send_email(to, subject, body, attachment=None):
        sent.append({"to": to, "subject": subject, "body": body, "attachment": attachment})

    monkeypatch.setattr("app.services.email.send_email", fake_send_email)
    return sent


def _approved_budget_items(client, headers, project):
    return client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara IP", "quantity": 1, "unit_price": 100}]},
        headers=headers,
    ).json()


def test_creating_a_quote_notifies_active_admins(client, admin_token, oficina_token, db_session, monkeypatch):
    sent = _capture_emails(monkeypatch)
    admin_headers = auth_headers(admin_token)

    # segundo admin activo + un admin inactivo -> no debe recibir nada
    create_user(db_session, "admin2@test.com", "adminpass123", "admin")
    inactive_admin = create_user(db_session, "admin3@test.com", "adminpass123", "admin")
    inactive_admin.is_active = False
    db_session.commit()

    project = make_project(client, admin_headers)
    budget = _approved_budget_items(client, admin_headers, project)
    client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=admin_headers)

    recipients = {e["to"] for e in sent}
    assert "admin@test.com" in recipients
    assert "admin2@test.com" in recipients
    assert "admin3@test.com" not in recipients
    assert all("pendiente de aprobar" in e["subject"] for e in sent)


def test_assigning_technician_to_ticket_sends_notification(client, admin_token, db_session, monkeypatch):
    sent = _capture_emails(monkeypatch)
    headers = auth_headers(admin_token)
    technician = create_user(db_session, "assignee@test.com", "tecpass123", "tecnico")
    project = make_project(client, headers)

    created = client.post(
        f"/api/projects/{project['id']}/tickets",
        json={"problem": "No enciende", "technician_id": technician.id},
        headers=headers,
    ).json()
    assert any(e["to"] == "assignee@test.com" and "asignado" in e["subject"] for e in sent)

    sent.clear()
    # reasignar al mismo técnico no debería re-notificar
    client.put(f"/api/tickets/{created['id']}", json={"technician_id": technician.id}, headers=headers)
    assert sent == []

    other_tech = create_user(db_session, "other@test.com", "tecpass123", "tecnico")
    client.put(f"/api/tickets/{created['id']}", json={"technician_id": other_tech.id}, headers=headers)
    assert any(e["to"] == "other@test.com" for e in sent)


def test_ticket_without_technician_sends_no_notification(client, admin_token, monkeypatch):
    sent = _capture_emails(monkeypatch)
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    client.post(f"/api/projects/{project['id']}/tickets", json={"problem": "Cámara desconectada"}, headers=headers)
    assert sent == []


def test_issuing_invoice_emails_client_with_pdf_attached(client, admin_token, db_session, monkeypatch):
    sent = _capture_emails(monkeypatch)
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")

    client_resp = client.post(
        "/api/clients", json={"name": "Cliente con correo", "email": "cliente@test.com"}, headers=headers
    ).json()
    project = client.post("/api/projects", json={"client_id": client_resp["id"]}, headers=headers).json()
    budget = _approved_budget_items(client, headers, project)
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()

    sent.clear()  # descarta el correo de "cotización pendiente" disparado arriba
    client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)

    assert len(sent) == 1
    assert sent[0]["to"] == "cliente@test.com"
    assert "emitida" in sent[0]["subject"]
    assert sent[0]["attachment"] is not None
    filename, content, mime_type = sent[0]["attachment"]
    assert filename.endswith(".pdf")
    assert content[:4] == b"%PDF"
    assert mime_type == "application/pdf"


def test_invoice_without_client_email_sends_nothing(client, admin_token, db_session, monkeypatch):
    sent = _capture_emails(monkeypatch)
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")

    project = make_project(client, headers)  # cliente de prueba sin email
    budget = _approved_budget_items(client, headers, project)
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()

    sent.clear()
    client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)
    assert sent == []


def test_send_email_without_smtp_configured_does_not_raise():
    from app.services.email import send_email

    send_email("someone@example.com", "Asunto de prueba", "Cuerpo de prueba")
