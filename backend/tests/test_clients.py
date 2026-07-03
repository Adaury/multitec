from tests.conftest import auth_headers


def test_create_list_get_update_client(client, admin_token):
    headers = auth_headers(admin_token)

    create_resp = client.post(
        "/api/clients",
        json={"name": "Ferretería Ejemplo", "rnc": "130123456", "phone": "8095551111"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    client_id = create_resp.json()["id"]

    list_resp = client.get("/api/clients", headers=headers)
    assert list_resp.status_code == 200
    assert any(c["id"] == client_id for c in list_resp.json())

    get_resp = client.get(f"/api/clients/{client_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Ferretería Ejemplo"

    update_resp = client.put(
        f"/api/clients/{client_id}",
        json={"name": "Ferretería Ejemplo Actualizada", "rnc": "130123456"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Ferretería Ejemplo Actualizada"


def test_get_unknown_client_404(client, admin_token):
    resp = client.get("/api/clients/999999", headers=auth_headers(admin_token))
    assert resp.status_code == 404
