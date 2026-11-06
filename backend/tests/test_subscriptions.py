from datetime import date, datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.notification import Notification
from app.models.user import User
from app.services.subscriptions import add_months
from tests.conftest import auth_headers, create_user

SIGNUP = {
    "company_name": "Seguridad Total SRL",
    "admin_name": "María Gómez",
    "email": "maria@seguridadtotal.com",
    "phone": "809-555-1234",
    "password": "ClaveSegura-2026",
    "accept_terms": True,
}


def _dt(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _login(client, email, password):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _platform(client, db_session):
    create_user(db_session, "owner@test.com", "ownerpass1234", "admin", is_platform_admin=True)
    return auth_headers(_login(client, "owner@test.com", "ownerpass1234"))


def _signup(client, **changes):
    resp = client.post("/api/signup", json={**SIGNUP, **changes})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _company(name=SIGNUP["company_name"]) -> Company:
    with SessionLocal(bypass_tenant=True) as db:
        company = db.query(Company).filter(Company.name == name).one()
        db.expunge(company)
        return company


def _set(company_id: int, **values) -> None:
    with SessionLocal(bypass_tenant=True) as db:
        db.query(Company).filter(Company.id == company_id).update(values)
        db.commit()


def test_add_months_keeps_the_day_or_uses_the_last_one():
    assert add_months(datetime(2026, 1, 31), 1) == datetime(2026, 2, 28)
    assert add_months(datetime(2026, 11, 15), 2) == datetime(2027, 1, 15)


def test_a_company_signs_up_alone_with_a_trial_and_the_base_catalog(client, db_session):
    platform = _platform(client, db_session)
    info = client.get("/api/signup/info").json()
    assert info["enabled"] and info["trial_days"] == 45 and info["currency"] == "USD"
    assert [p["name"] for p in info["plans"]] == ["Básico", "Profesional", "Empresarial"]

    done = _signup(client)
    assert done["trial_days"] == 45

    company = _company()
    assert company.source == "registro" and company.state == "prueba" and 44 <= company.days_left <= 45
    # Quien se registró entra con la clave que eligió, sin tener que cambiarla.
    token = _login(client, SIGNUP["email"], SIGNUP["password"])
    me = client.get("/api/auth/me", headers=auth_headers(token)).json()
    assert me["company_name"] == "Seguridad Total SRL" and me["role"] == "admin" and not me["must_change_password"]
    catalog = client.get("/api/catalog", headers=auth_headers(token)).json()
    assert len(catalog) > 250 and all(p["price"] == 0 for p in catalog)

    # A la plataforma le llega el aviso y la solicitud sale en el resumen hasta marcarla vista.
    with SessionLocal(bypass_tenant=True) as db:
        assert db.query(Notification).filter(Notification.title.contains("Seguridad Total")).count() == 1
    summary = client.get("/api/platform/summary", headers=platform).json()
    assert [r["name"] for r in summary["new_requests"]] == ["Seguridad Total SRL"]
    client.post(f"/api/platform/companies/{company.id}/reviewed", headers=platform)
    assert client.get("/api/platform/summary", headers=platform).json()["new_requests"] == []


def test_signup_rejects_robots_duplicates_and_missing_terms(client, monkeypatch):
    assert client.post("/api/signup", json={**SIGNUP, "website": "http://spam"}).status_code == 400
    assert client.post("/api/signup", json={**SIGNUP, "accept_terms": False}).status_code == 400
    assert client.post("/api/signup", json={**SIGNUP, "password": "corta"}).status_code == 422
    _signup(client)
    dup = client.post("/api/signup", json={**SIGNUP, "company_name": "Otra SRL"})
    assert dup.status_code == 400 and "Ya existe" in dup.json()["detail"]

    monkeypatch.setattr(get_settings(), "public_signup_enabled", False)
    assert client.post("/api/signup", json={**SIGNUP, "email": "otro@x.com"}).status_code == 404


def test_payments_move_paid_until_and_end_the_trial(client, db_session):
    platform = _platform(client, db_session)
    _signup(client)
    company = _company()

    detail = client.post(
        f"/api/platform/companies/{company.id}/payments",
        json={"kind": "instalacion", "amount": 10000, "months": 1, "method": "transferencia", "reference": "BHD-123"},
        headers=platform,
    ).json()
    assert detail["state"] == "activa" and detail["trial_ends_at"] is None and detail["setup_paid_at"]
    first = _dt(detail["paid_until"])
    assert 27 <= (first - datetime.now(timezone.utc)).days <= 31

    detail = client.post(
        f"/api/platform/companies/{company.id}/payments",
        json={"kind": "mensualidad", "amount": 2500, "months": 1, "method": "efectivo"},
        headers=platform,
    ).json()
    assert _dt(detail["paid_until"]) > first and len(detail["payments"]) == 2

    summary = client.get("/api/platform/summary", headers=platform).json()
    assert summary["collected_this_month"] == 12500 and summary["paying_companies"] == 1
    assert summary["expected_monthly"] == 60  # plan Profesional (el destacado), en US$

    # El administrador de la empresa ve lo suyo en «Mi suscripción»; un técnico no.
    token = _login(client, SIGNUP["email"], SIGNUP["password"])
    mine = client.get("/api/subscription", headers=auth_headers(token)).json()
    assert mine["state"] == "activa" and mine["setup_paid"] and [p["amount"] for p in mine["payments"]] == [2500, 10000]


def test_an_unpaid_month_warns_first_and_then_cuts_access(client, db_session):
    _signup(client)
    company = _company()
    now = datetime.now(timezone.utc)

    _set(company.id, trial_ends_at=None, paid_until=now - timedelta(days=2))  # dentro de los días de gracia
    token = _login(client, SIGNUP["email"], SIGNUP["password"])
    mine = client.get("/api/subscription", headers=auth_headers(token)).json()
    assert mine["state"] == "atrasada" and "venció" in mine["notice"]

    _set(company.id, paid_until=now - timedelta(days=6))  # pasaron los días de gracia
    assert client.get("/api/clients", headers=auth_headers(token)).status_code == 403
    blocked = client.post("/api/auth/login", data={"username": SIGNUP["email"], "password": SIGNUP["password"]})
    assert blocked.status_code == 403 and "mensualidad" in blocked.json()["detail"]

    _set(company.id, trial_ends_at=now - timedelta(days=1), paid_until=None)  # prueba terminada sin pagar
    assert client.post("/api/auth/login", data={"username": SIGNUP["email"], "password": SIGNUP["password"]}).status_code == 403


def test_support_session_is_read_only_by_default_and_audited(client, db_session):
    platform = _platform(client, db_session)
    _signup(client)
    company = _company()
    owner_token = _login(client, SIGNUP["email"], SIGNUP["password"])
    client.post("/api/clients", json={"name": "Cliente de la empresa B"}, headers=auth_headers(owner_token))

    session = client.post(f"/api/platform/companies/{company.id}/support-session", headers=platform).json()
    assert session["company_name"] == "Seguridad Total SRL" and session["allow_changes"] is False
    support = auth_headers(session["access_token"])

    me = client.get("/api/auth/me", headers=support).json()
    assert me["support_mode"] and not me["support_write"] and me["company_id"] == company.id
    names = [c["name"] for c in client.get("/api/clients", headers=support).json()]
    assert names == ["Cliente de la empresa B"]  # ve los datos de la empresa atendida, no los de Multitec
    denied = client.post("/api/clients", json={"name": "No debería"}, headers=support)
    assert denied.status_code == 403 and "solo lectura" in denied.json()["detail"]
    # Con el token de soporte no se usa el panel de plataforma.
    assert client.get("/api/platform/companies", headers=support).status_code == 403

    writable = client.post(f"/api/platform/companies/{company.id}/support-session", json={"allow_changes": True},
                           headers=platform).json()
    created = client.post("/api/clients", json={"name": "Corregido por soporte"}, headers=auth_headers(writable["access_token"]))
    assert created.status_code == 201, created.text

    with SessionLocal(bypass_tenant=True) as db:
        actions = {a for (a,) in db.query(AuditLog.action).filter(AuditLog.company_id == company.id)}
        assert {"support_session_started", "support_change"} <= actions
        owner = db.query(User).filter(User.email == "owner@test.com").one()
        assert owner.company_id == 1 and owner.is_platform_admin  # su cuenta real no cambió

    # Soporte entra aunque la empresa esté suspendida (justo para ayudarla); un admin normal no puede abrir soporte.
    _set(company.id, is_active=False)
    again = client.post(f"/api/platform/companies/{company.id}/support-session", headers=platform).json()
    assert client.get("/api/clients", headers=auth_headers(again["access_token"])).status_code == 200
    assert client.post(f"/api/platform/companies/{company.id}/support-session", headers=auth_headers(owner_token)).status_code in (401, 403)


def test_platform_can_set_custom_fees_and_fix_paid_until(client, db_session):
    platform = _platform(client, db_session)
    _signup(client)
    company = _company()
    out = client.put(f"/api/platform/companies/{company.id}",
                     json={"setup_fee": 8000, "monthly_fee": 2000, "paid_until": str(date.today() + timedelta(days=10))},
                     headers=platform).json()
    assert out["setup_fee"] == 8000 and out["monthly_fee"] == 2000 and out["state"] == "activa" and out["days_left"] >= 8
    out = client.put(f"/api/platform/companies/{company.id}", json={"clear_fees": True}, headers=platform).json()
    assert out["setup_fee"] == 160 and out["monthly_fee"] == 60  # vuelve a la tarifa de su plan


def test_signup_takes_the_chosen_plan_and_its_user_limit(client):
    plans = client.get("/api/signup/info").json()["plans"]
    basico = next(p for p in plans if p["name"] == "Básico")
    _signup(client, plan_id=basico["id"])
    company = _company()
    assert company.plan_id == basico["id"] and company.max_users == 4
    token = _login(client, SIGNUP["email"], SIGNUP["password"])
    mine = client.get("/api/subscription", headers=auth_headers(token)).json()
    assert mine["plan_name"] == "Básico" and mine["monthly_fee"] == 40 and mine["currency"] == "USD"
    assert mine["contact_phones"] == ["829-283-1336", "829-477-8613"]
    assert client.post("/api/signup", json={**SIGNUP, "email": "x@y.com", "plan_id": 9999}).status_code == 400


def test_public_site_shows_only_real_published_testimonials(client, db_session):
    platform = _platform(client, db_session)
    site = client.get("/api/site").json()
    assert len(site["plans"]) == 3 and site["testimonials"] == [] and site["phones"][0] == "829-283-1336"

    admin = client.get("/api/platform/site", headers=platform).json()
    example = admin["testimonials"][0]
    assert example["is_example"] and not example["published"]
    # Un ejemplo no se publica sin cambiar su texto.
    bad = client.put(f"/api/platform/site/testimonials/{example['id']}", json={**example, "published": True}, headers=platform)
    assert bad.status_code == 400
    real = {**example, "author": "Pedro Rosario", "company": "Alarmas del Cibao",
            "quote": "Ahora cotizamos el mismo día que hacemos la visita.", "published": True}
    assert client.put(f"/api/platform/site/testimonials/{example['id']}", json=real, headers=platform).status_code == 200
    shown = client.get("/api/site").json()["testimonials"]
    assert [t["author"] for t in shown] == ["Pedro Rosario"]

    # Editar un plan cambia lo que ve todo el mundo; un plan en uso no se borra, se oculta.
    plan = admin["plans"][0]
    client.put(f"/api/platform/site/plans/{plan['id']}", json={**plan, "monthly_price": 45}, headers=platform)
    assert client.get("/api/site").json()["plans"][0]["monthly_price"] == 45
    _signup(client, plan_id=plan["id"])
    client.delete(f"/api/platform/site/plans/{plan['id']}", headers=platform)
    assert all(p["id"] != plan["id"] for p in client.get("/api/site").json()["plans"])
    assert any(p["id"] == plan["id"] and not p["active"] for p in client.get("/api/platform/site", headers=platform).json()["plans"])

    # Nadie más puede editar el sitio.
    owner = auth_headers(_login(client, SIGNUP["email"], SIGNUP["password"]))
    assert client.post("/api/platform/site/testimonials", json=real, headers=owner).status_code == 403


def test_a_client_sends_its_experience_and_the_owner_publishes_it(client, db_session):
    platform = _platform(client, db_session)
    experience = {
        "author": "Carmen Díaz",
        "company": "Colmado La Esquina",
        "quote": "Me instalaron las cámaras en un día y las veo desde el celular.",
        "rating": 5,
        "contact": "809-555-7788",
        "consent": True,
    }
    assert client.post("/api/site/experiences", json={**experience, "consent": False}).status_code == 400
    assert client.post("/api/site/experiences", json={**experience, "website": "spam"}).status_code == 400
    assert client.post("/api/site/experiences", json=experience).status_code == 201

    # Llega como borrador del cliente: no sale en la página y al dueño le llega el aviso.
    assert client.get("/api/site").json()["testimonials"] == []
    sent = next(t for t in client.get("/api/platform/site", headers=platform).json()["testimonials"] if t["source"] == "cliente")
    assert sent["author"] == "Carmen Díaz" and sent["contact"] == "809-555-7788" and not sent["published"]
    with SessionLocal(bypass_tenant=True) as db:
        assert db.query(Notification).filter(Notification.title.contains("Carmen Díaz")).count() == 1

    client.put(f"/api/platform/site/testimonials/{sent['id']}", json={**sent, "published": True}, headers=platform)
    shown = client.get("/api/site").json()["testimonials"]
    assert [t["author"] for t in shown] == ["Carmen Díaz"] and shown[0]["contact"] is None  # el contacto nunca se publica
    stored = next(t for t in client.get("/api/platform/site", headers=platform).json()["testimonials"] if t["id"] == sent["id"])
    assert stored["source"] == "cliente" and stored["contact"] == "809-555-7788"


def test_partners_show_on_the_public_site_only_when_published(client, db_session):
    platform = _platform(client, db_session)
    created = client.post("/api/platform/site/partners", headers=platform, json={
        "name": "FHONS SRL", "description": "Tecnología para oficinas y redes", "url": "www.fhons.com.do",
    })
    assert created.status_code == 201 and created.json()["url"] == "https://www.fhons.com.do"
    assert [p["name"] for p in client.get("/api/site").json()["partners"]] == ["FHONS SRL"]
    partner = created.json()
    client.put(f"/api/platform/site/partners/{partner['id']}", json={**partner, "published": False}, headers=platform)
    assert client.get("/api/site").json()["partners"] == []
    # No se enlazan logos de otros sitios.
    bad = client.post("/api/platform/site/partners", headers=platform, json={"name": "Otro", "logo_url": "https://otro.com/logo.png"})
    assert bad.status_code == 422
