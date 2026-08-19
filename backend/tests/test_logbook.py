from tests.conftest import auth_headers, make_project


def test_create_and_list_log_entry(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    resp = client.post(
        f"/api/projects/{project['id']}/logbook", json={"comment": "Se instaló el rack"}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["comment"] == "Se instaló el rack"

    listed = client.get(f"/api/projects/{project['id']}/logbook", headers=headers).json()
    assert len(listed) == 1


def test_create_log_entry_for_missing_project_fails(client, admin_token):
    resp = client.post(
        "/api/projects/999999/logbook", json={"comment": "x"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 404
