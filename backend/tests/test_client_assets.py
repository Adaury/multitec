"""Equipos instalados por cliente: serial, MAC, ubicación y garantía."""

from datetime import timedelta

from app.core.timeutil import today_dr
from tests.conftest import assign_to_tecnico, auth_headers, make_project


def _asset(client, headers, client_id, **extra):
    body = {"kind": "camara", "name": "Cámara domo 4MP", "serial": "SN-001", **extra}
    resp = client.post(f"/api/clients/{client_id}/assets", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_register_edit_and_list_an_installed_asset(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers, client_name="Hotel Costa Azul")
    created = _asset(
        client,
        headers,
        project["client_id"],
        brand="Hikvision",
        model="DS-2CD2143",
        mac="aa-bb-cc-dd-ee-ff",
        ip_address="192.168.1.64",
        location="Entrada principal",
        installed_on="2026-10-01",
        project_id=project["id"],
    )
    assert created["mac"] == "AA:BB:CC:DD:EE:FF"  # se normaliza
    assert created["warranty_status"] is None

    edited = client.put(
        f"/api/client-assets/{created['id']}", json={"location": "Parqueo", "serial": ""}, headers=headers
    ).json()
    assert edited["location"] == "Parqueo" and edited["serial"] is None and edited["brand"] == "Hikvision"

    listed = client.get(f"/api/clients/{project['client_id']}/assets", headers=headers).json()
    assert [a["id"] for a in listed] == [created["id"]]


def test_warranty_status_is_computed(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    today = today_dr()
    cases = {
        "vencida": today - timedelta(days=1),
        "por_vencer": today + timedelta(days=30),
        "vigente": today + timedelta(days=400),
    }
    for expected, until in cases.items():
        asset = _asset(client, headers, project["client_id"], name=expected, serial=None, warranty_until=until.isoformat())
        assert asset["warranty_status"] == expected


def test_asset_validation(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    other = make_project(client, headers, client_name="Otro cliente")
    url = f"/api/clients/{project['client_id']}/assets"

    assert client.post(url, json={"name": "x", "mac": "no-es-mac"}, headers=headers).status_code == 422
    assert client.post(url, json={"name": "x", "kind": "nave_espacial"}, headers=headers).status_code == 422
    assert client.post(url, json={"name": ""}, headers=headers).status_code == 422
    # El proyecto debe ser del mismo cliente.
    assert client.post(url, json={"name": "x", "project_id": other["id"]}, headers=headers).status_code == 400
    assert client.post("/api/clients/99999/assets", json={"name": "x"}, headers=headers).status_code == 404


def test_technician_only_sees_assets_of_their_own_clients_and_cannot_delete(client, admin_token, tecnico_token, db_session):
    admin = auth_headers(admin_token)
    tec = auth_headers(tecnico_token)
    mine = make_project(client, admin, client_name="Cliente mío")
    assign_to_tecnico(db_session, mine)
    foreign = make_project(client, admin, client_name="Cliente ajeno")
    my_asset = _asset(client, admin, mine["client_id"])
    foreign_asset = _asset(client, admin, foreign["client_id"], name="Ajeno")

    assert client.get(f"/api/clients/{mine['client_id']}/assets", headers=tec).status_code == 200
    assert client.get(f"/api/clients/{foreign['client_id']}/assets", headers=tec).status_code == 404
    assert client.post(f"/api/clients/{foreign['client_id']}/assets", json={"name": "x"}, headers=tec).status_code == 404
    assert client.put(f"/api/client-assets/{foreign_asset['id']}", json={"name": "y"}, headers=tec).status_code == 404

    # En campo registra y corrige lo suyo, pero borrar es de oficina.
    assert client.post(f"/api/clients/{mine['client_id']}/assets", json={"name": "Nuevo en sitio"}, headers=tec).status_code == 201
    assert client.put(f"/api/client-assets/{my_asset['id']}", json={"location": "Sala"}, headers=tec).status_code == 200
    assert client.delete(f"/api/client-assets/{my_asset['id']}", headers=tec).status_code == 403


def test_deleting_an_asset_is_audited(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    asset = _asset(client, headers, project["client_id"], serial="SN-BORRAR")
    assert client.delete(f"/api/client-assets/{asset['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/clients/{project['client_id']}/assets", headers=headers).json() == []
    rows = client.get("/api/audit", params={"action": "client_asset_deleted"}, headers=headers).json()
    assert rows and "SN-BORRAR" in rows[0]["detail"]
