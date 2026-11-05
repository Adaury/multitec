from tests.conftest import auth_headers, make_project


def test_saving_engineering_creates_it_when_the_project_had_none(client, admin_token, db_session):
    """Un proyecto sin fila de ingeniería (datos viejos o importados): guardar la crea en vez de responder 404."""
    from app.models.engineering import Engineering

    h = auth_headers(admin_token)
    project = make_project(client, h)
    db_session.query(Engineering).filter(Engineering.project_id == project["id"]).delete()
    db_session.commit()
    assert client.get(f"/api/projects/{project['id']}/engineering", headers=h).status_code == 404

    saved = client.put(
        f"/api/projects/{project['id']}/engineering",
        json={"recommended_equipment": "4 cámaras IP 4MP", "observations": "Pared de concreto"},
        headers=h,
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["recommended_equipment"] == "4 cámaras IP 4MP" and body["ai_generated"] is False

    again = client.get(f"/api/projects/{project['id']}/engineering", headers=h).json()
    assert again["observations"] == "Pared de concreto"


def test_saving_engineering_of_a_missing_project_is_404(client, admin_token):
    h = auth_headers(admin_token)
    assert client.put("/api/projects/999999/engineering", json={"wiring": "x"}, headers=h).status_code == 404
