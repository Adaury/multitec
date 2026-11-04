"""Cotización en formato «monto general» y envío al cliente por correo con el PDF adjunto."""

from app.services import email as email_service
from tests.conftest import auth_headers, make_project


def _quote(client, headers, project):
    return client.post(
        f"/api/projects/{project['id']}/quotes",
        json={"items": [{"description": "Cámara IP 4MP", "quantity": 4, "unit_price": 3500}]},
        headers=headers,
    ).json()


def test_global_variant_is_a_distinct_pdf(client, admin_token):
    headers = auth_headers(admin_token)
    quote = _quote(client, headers, make_project(client, headers))

    detailed = client.get(f"/api/quotes/{quote['id']}/pdf", headers=headers)
    general = client.get(f"/api/quotes/{quote['id']}/pdf?variant=global", headers=headers)
    assert general.status_code == 200
    assert general.content[:4] == b"%PDF"
    assert f'{quote["code"]}-monto-general.pdf' in general.headers["content-disposition"]
    assert general.content != detailed.content


def test_unknown_variant_is_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    quote = _quote(client, headers, make_project(client, headers))
    assert client.get(f"/api/quotes/{quote['id']}/pdf?variant=otra", headers=headers).status_code == 422


def test_send_email_without_smtp_explains_instead_of_pretending(client, admin_token, monkeypatch):
    monkeypatch.setattr(email_service, "is_configured", lambda: False)
    headers = auth_headers(admin_token)
    quote = _quote(client, headers, make_project(client, headers))

    resp = client.post(f"/api/quotes/{quote['id']}/send-email", json={"to": "cliente@example.com"}, headers=headers)
    assert resp.status_code == 409
    assert "SMTP" in resp.json()["detail"]


def test_send_email_attaches_chosen_format_and_records_history(client, admin_token, monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(
        email_service, "deliver_email", lambda to, subject, body, attachment=None: sent.append((to, subject, attachment))
    )
    headers = auth_headers(admin_token)
    quote = _quote(client, headers, make_project(client, headers))

    resp = client.post(
        f"/api/quotes/{quote['id']}/send-email",
        json={"to": "cliente@example.com", "variant": "global"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filename"] == f"{quote['code']}-monto-general.pdf"
    to, subject, attachment = sent[0]
    assert to == "cliente@example.com"
    assert quote["code"] in subject
    assert attachment[0] == f"{quote['code']}-monto-general.pdf" and attachment[1][:4] == b"%PDF"

    history = client.get(f"/api/quotes/{quote['id']}/history", headers=headers).json()
    assert any(h["action"] == "enviada" and "monto general" in (h["note"] or "") for h in history)


def test_send_email_smtp_failure_is_reported(client, admin_token, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("conexión rechazada")

    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "deliver_email", boom)
    headers = auth_headers(admin_token)
    quote = _quote(client, headers, make_project(client, headers))

    resp = client.post(f"/api/quotes/{quote['id']}/send-email", json={"to": "cliente@example.com"}, headers=headers)
    assert resp.status_code == 502


def test_technician_cannot_send(client, tecnico_token):
    resp = client.post("/api/quotes/1/send-email", json={"to": "cliente@example.com"}, headers=auth_headers(tecnico_token))
    assert resp.status_code == 403
