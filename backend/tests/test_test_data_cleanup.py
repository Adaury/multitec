from datetime import date

from app.db.session import SessionLocal
from app.models.company import Company
from app.models.purchase_invoice import PurchaseInvoice
from app.models.supplier import Supplier
from app.services import catalog_base
from tests.conftest import auth_headers, create_user, make_category, seed_ncf_sequence


def _client_with_everything(client, h, name: str, product_id: int | None = None) -> dict:
    c = client.post("/api/clients", json={"name": name}, headers=h).json()
    project = client.post("/api/projects", json={"client_id": c["id"]}, headers=h).json()
    item = {"description": "Cámara IP", "quantity": 1, "unit_price": 100}
    if product_id:
        item["product_id"] = product_id
    budget = client.post(f"/api/projects/{project['id']}/budgets", json={"items": [item]}, headers=h).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=h).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=h)
    pre = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=h).json()
    invoice = client.post(f"/api/pre-invoices/{pre['id']}/convert-to-invoice", headers=h).json()
    client.post(f"/api/projects/{project['id']}/tickets", json={"problem": "Prueba de ticket"}, headers=h)
    return {"client": c, "project": project, "quote": quote, "invoice": invoice}


def test_test_clients_are_flagged_and_deleted_with_everything_they_own(client, admin_token, db_session):
    h = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    category = make_category(client, h)
    product = client.post("/api/catalog", json={"category_id": category["id"], "name": "Cámara IP 4MP", "price": 4500}, headers=h).json()
    fake = _client_with_everything(client, h, "Smoke Test Client", product["id"])
    real = _client_with_everything(client, h, "Ferretería Real SRL", product["id"])
    # Una compra (606) asociada al proyecto de prueba: es fiscal y se conserva, solo se suelta del proyecto.
    supplier = Supplier(name="Suplidor", rnc="101000001")
    db_session.add(supplier)
    db_session.flush()
    db_session.add(PurchaseInvoice(supplier_id=supplier.id, ncf="B0100000099", invoice_date=date.today(),
                                   goods_amount=100, project_id=fake["project"]["id"]))
    db_session.commit()

    listing = client.get("/api/admin/test-data", headers=h).json()
    flags = {c["name"]: c for c in listing["clients"]}
    assert flags["Smoke Test Client"]["suspect"] is True and flags["Ferretería Real SRL"]["suspect"] is False
    assert flags["Smoke Test Client"]["fiscal_invoices"] == 1

    preview = client.post("/api/admin/test-data/preview", json={"client_ids": [fake["client"]["id"]]}, headers=h).json()
    counts = {c["key"]: c["count"] for c in preview["counts"]}
    assert counts["clients"] == 1 and counts["projects"] == 1 and counts["quotes"] == 1 and counts["invoices"] == 1
    assert counts["tickets"] == 1
    assert [f["ncf"] for f in preview["fiscal_invoices"]] == [fake["invoice"]["ncf"]]
    # La vista previa no borra nada.
    assert client.get(f"/api/projects/{fake['project']['id']}", headers=h).status_code == 200

    # Sin la palabra de confirmación no se borra.
    refused = client.post("/api/admin/test-data/delete", json={"client_ids": [fake["client"]["id"]], "confirm": "si"}, headers=h)
    assert refused.status_code == 400

    done = client.post("/api/admin/test-data/delete", json={"client_ids": [fake["client"]["id"]], "confirm": "borrar"}, headers=h)
    assert done.status_code == 200, done.text
    assert client.get(f"/api/projects/{fake['project']['id']}", headers=h).status_code == 404
    assert client.get(f"/api/clients/{fake['client']['id']}", headers=h).status_code == 404

    # Lo real sigue intacto, igual que el producto y la compra (ahora sin proyecto).
    assert client.get(f"/api/projects/{real['project']['id']}", headers=h).status_code == 200
    assert client.get(f"/api/quotes/{real['quote']['id']}", headers=h).status_code == 200
    assert any(p["id"] == product["id"] for p in client.get("/api/catalog", headers=h).json())
    with SessionLocal(company_id=1) as db:
        purchase = db.query(PurchaseInvoice).one()
        assert purchase.project_id is None

    assert any(r["action"] == "test_data.delete" for r in client.get("/api/audit", headers=h).json())


def test_deleting_a_product_keeps_the_quote_line_text(client, admin_token):
    h = auth_headers(admin_token)
    category = make_category(client, h)
    product = client.post("/api/catalog", json={"category_id": category["id"], "name": "Producto de prueba", "price": 10}, headers=h).json()
    c = client.post("/api/clients", json={"name": "Cliente real"}, headers=h).json()
    project = client.post("/api/projects", json={"client_id": c["id"]}, headers=h).json()
    budget = client.post(f"/api/projects/{project['id']}/budgets",
                         json={"items": [{"product_id": product["id"], "description": "Producto de prueba", "quantity": 2, "unit_price": 10}]},
                         headers=h).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=h).json()

    listing = client.get("/api/admin/test-data", headers=h).json()
    assert next(p for p in listing["products"] if p["id"] == product["id"])["suspect"] is True

    res = client.post("/api/admin/test-data/delete", json={"product_ids": [product["id"]], "confirm": "BORRAR"}, headers=h)
    assert res.status_code == 200, res.text
    assert not any(p["id"] == product["id"] for p in client.get("/api/catalog", headers=h).json())
    items = client.get(f"/api/quotes/{quote['id']}", headers=h).json()["items"]
    assert [(i["description"], i["product_id"]) for i in items] == [("Producto de prueba", None)]


def test_cleanup_is_admin_only_and_never_reaches_another_company(client, admin_token, oficina_token, db_session):
    h = auth_headers(admin_token)
    assert client.get("/api/admin/test-data", headers=auth_headers(oficina_token)).status_code == 403

    with SessionLocal(bypass_tenant=True) as db:
        db.add(Company(id=2, name="Empresa B", slug="empresa-b"))
        db.commit()
    create_user(db_session, "b@test.com", "passwordB-1234", "admin", company_id=2)
    token_b = client.post("/api/auth/login", data={"username": "b@test.com", "password": "passwordB-1234"}).json()["access_token"]
    other = client.post("/api/clients", json={"name": "Test de la empresa B"}, headers=auth_headers(token_b)).json()

    assert all(c["id"] != other["id"] for c in client.get("/api/admin/test-data", headers=h).json()["clients"])
    res = client.post("/api/admin/test-data/delete", json={"client_ids": [other["id"]], "confirm": "BORRAR"}, headers=h)
    assert res.status_code == 400  # para la empresa 1 ese cliente no existe: no hay nada que borrar
    assert client.get(f"/api/clients/{other['id']}", headers=auth_headers(token_b)).status_code == 200


def test_base_catalog_creates_items_without_price_and_never_touches_existing_ones(client, admin_token):
    h = auth_headers(admin_token)
    kits = client.get("/api/catalog/base-kits", headers=h).json()
    assert {"cctv", "alarma", "cerco", "domotica", "acceso", "redes", "incendio", "electrico", "ferreteria"} <= {k["kind"] for k in kits}

    # Un artículo que ya existe con su precio no se cambia.
    cerco = make_category(client, h, name="Cerco Eléctrico", code_prefix="CER")
    mine = client.post("/api/catalog", json={"category_id": cerco["id"], "name": "Energizador de cerco eléctrico 5000 m", "price": 7000}, headers=h).json()

    preview = client.post("/api/catalog/base-catalog", headers=h).json()
    total = len(catalog_base.all_rows())
    assert preview["dry_run"] and preview["errors"] == 0 and preview["created"] == total - 1 and preview["skipped"] == 1
    assert len(client.get("/api/catalog", headers=h).json()) == 1  # la vista previa no crea nada

    done = client.post("/api/catalog/base-catalog", params={"dry_run": False}, headers=h).json()
    assert done["created"] == total - 1 and done["errors"] == 0
    catalog = {p["name"]: p for p in client.get("/api/catalog", headers=h).json()}
    assert catalog["Energizador de cerco eléctrico 5000 m"]["price"] == 7000
    sensor = catalog["Sensor de movimiento PIR"]
    assert sensor["price"] == 0 and sensor["price_estimated"] is True and sensor["code"].startswith("ALM-")
    assert catalog["Cámara IP domo 4 MP"]["category_path"].startswith("CCTV")

    # Cargarlo otra vez no duplica nada.
    again = client.post("/api/catalog/base-catalog", params={"dry_run": False}, headers=h).json()
    assert again["created"] == 0 and again["skipped"] == total


def test_every_base_kit_downloads_as_a_template(client, admin_token):
    h = auth_headers(admin_token)
    for kind in catalog_base.KIT_ORDER:
        res = client.get("/api/catalog/import-template", params={"kind": kind, "format": "xlsx"}, headers=h)
        assert res.status_code == 200, kind
    assert client.get("/api/catalog/import-template", params={"kind": "inventado"}, headers=h).status_code == 400
