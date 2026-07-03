from tests.conftest import auth_headers, create_user, make_project


def test_list_technicians_only_active_tecnico_role(client, admin_token, oficina_token, db_session):
    headers = auth_headers(admin_token)
    create_user(db_session, "tec1@test.com", "tecpass123", "tecnico")
    inactive = create_user(db_session, "tec2@test.com", "tecpass123", "tecnico")
    inactive.is_active = False
    db_session.commit()
    create_user(db_session, "oficina2@test.com", "oficinapass123", "oficina")

    resp = client.get("/api/users/technicians", headers=headers)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert names == ["tec1"]

    # accesible también para oficina, no solo admin
    resp_oficina = client.get("/api/users/technicians", headers=auth_headers(oficina_token))
    assert resp_oficina.status_code == 200


def test_assign_technician_to_ticket(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    tecnico = create_user(db_session, "assignee@test.com", "tecpass123", "tecnico")
    project = make_project(client, headers)

    created = client.post(
        f"/api/projects/{project['id']}/tickets", json={"problem": "No graba de noche"}, headers=headers
    ).json()
    assert created["technician_id"] is None

    updated = client.put(
        f"/api/tickets/{created['id']}", json={"technician_id": tecnico.id}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["technician_id"] == tecnico.id


def test_tecnico_can_create_ticket_preassigned_to_self(client, tecnico_token, admin_token, db_session):
    admin_headers = auth_headers(admin_token)
    tecnico_headers = auth_headers(tecnico_token)
    project = make_project(client, admin_headers)

    # tecnico_token fixture ya crea un usuario con role=tecnico en la BD
    from app.models.user import User

    tecnico_user = db_session.query(User).filter(User.email == "tecnico@test.com").one()

    created = client.post(
        f"/api/projects/{project['id']}/tickets",
        json={"problem": "Sensor de puerta desconectado", "technician_id": tecnico_user.id},
        headers=tecnico_headers,
    )
    assert created.status_code == 201
    assert created.json()["technician_id"] == tecnico_user.id
