import io

from tests.conftest import auth_headers, make_project


def _create_ticket(client, headers, project_id, problem="Cámara sin señal"):
    return client.post(
        f"/api/projects/{project_id}/tickets", json={"problem": problem}, headers=headers
    ).json()


def _upload_photo(client, headers, ticket_id, description=None):
    files = {"file": ("evidencia.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 50), "image/png")}
    data = {}
    if description:
        data["description"] = description
    return client.post(f"/api/tickets/{ticket_id}/photos", data=data, files=files, headers=headers)


def test_upload_photo_to_ticket(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    ticket = _create_ticket(client, headers, project["id"])

    resp = _upload_photo(client, headers, ticket["id"], description="Antes de la reparación")
    assert resp.status_code == 201
    assert resp.json()["description"] == "Antes de la reparación"

    ticket_after = client.get(f"/api/projects/{project['id']}/tickets", headers=headers).json()[0]
    assert len(ticket_after["assets"]) == 1


def test_upload_photo_rejects_disallowed_type(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    ticket = _create_ticket(client, headers, project["id"])

    files = {"file": ("nota.txt", io.BytesIO(b"no es una foto"), "text/plain")}
    resp = client.post(f"/api/tickets/{ticket['id']}/photos", files=files, headers=headers)
    assert resp.status_code == 400


def test_upload_photo_to_missing_ticket_fails(client, admin_token):
    headers = auth_headers(admin_token)
    resp = _upload_photo(client, headers, 999999)
    assert resp.status_code == 404


def test_delete_ticket_photo(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    ticket = _create_ticket(client, headers, project["id"])
    asset = _upload_photo(client, headers, ticket["id"]).json()

    deleted = client.delete(f"/api/tickets/{ticket['id']}/photos/{asset['id']}", headers=headers)
    assert deleted.status_code == 204

    ticket_after = client.get(f"/api/projects/{project['id']}/tickets", headers=headers).json()[0]
    assert ticket_after["assets"] == []


def test_delete_nonexistent_photo_returns_404(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    ticket = _create_ticket(client, headers, project["id"])

    resp = client.delete(f"/api/tickets/{ticket['id']}/photos/999999", headers=headers)
    assert resp.status_code == 404


def test_tecnico_can_upload_ticket_photo(client, tecnico_token, admin_token):
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)
    ticket = _create_ticket(client, admin_headers, project["id"])

    resp = _upload_photo(client, auth_headers(tecnico_token), ticket["id"])
    assert resp.status_code == 201
