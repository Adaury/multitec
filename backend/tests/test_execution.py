from tests.conftest import auth_headers, make_project


def test_advance_and_undo_stages(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    base = f"/api/projects/{project['id']}/execution"

    initial = client.get(base, headers=headers).json()
    assert initial["progress_percent"] == 0
    assert all(not s["completed"] for s in initial["stages"])

    advance_resp = client.post(f"{base}/advance", headers=headers)
    assert advance_resp.status_code == 200
    assert advance_resp.json()["progress_percent"] == 20
    assert advance_resp.json()["stages"][0]["completed"] is True

    undo_resp = client.post(f"{base}/undo", headers=headers)
    assert undo_resp.status_code == 200
    assert undo_resp.json()["progress_percent"] == 0


def test_advance_all_stages_then_reject_extra_advance(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    base = f"/api/projects/{project['id']}/execution"

    for _ in range(5):
        resp = client.post(f"{base}/advance", headers=headers)
        assert resp.status_code == 200

    final = client.get(base, headers=headers).json()
    assert final["progress_percent"] == 100
    assert all(s["completed"] for s in final["stages"])

    overshoot = client.post(f"{base}/advance", headers=headers)
    assert overshoot.status_code == 400


def test_undo_with_nothing_completed_fails(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    resp = client.post(f"/api/projects/{project['id']}/execution/undo", headers=headers)
    assert resp.status_code == 400
