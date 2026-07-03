import io

from tests.conftest import auth_headers, make_project


def _upload_photo(client, headers, project_id):
    files = {"file": ("foto.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 50), "image/png")}
    resp = client.post(
        f"/api/projects/{project_id}/survey/assets",
        data={"kind": "photo"},
        files=files,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_upload_and_edit_survey_notes(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    resp = client.put(
        f"/api/projects/{project['id']}/survey",
        json={"notes": "Notas originales", "measurements": "3x4m", "observations": "ninguna"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Notas originales"

    # las notas se pueden editar después
    resp = client.put(
        f"/api/projects/{project['id']}/survey",
        json={"notes": "Notas corregidas", "measurements": "3x4m", "observations": "ninguna"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Notas corregidas"


def test_upload_and_delete_survey_photo(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    asset = _upload_photo(client, headers, project["id"])
    assert asset["kind"] == "photo"

    survey = client.get(f"/api/projects/{project['id']}/survey", headers=headers).json()
    assert len(survey["assets"]) == 1

    delete_resp = client.delete(
        f"/api/projects/{project['id']}/survey/assets/{asset['id']}", headers=headers
    )
    assert delete_resp.status_code == 204

    survey = client.get(f"/api/projects/{project['id']}/survey", headers=headers).json()
    assert len(survey["assets"]) == 0


def test_delete_unknown_asset_404(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    resp = client.delete(f"/api/projects/{project['id']}/survey/assets/999999", headers=headers)
    assert resp.status_code == 404
