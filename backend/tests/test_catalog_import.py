import io

from app.services.catalog_import import parse_number, template_csv
from tests.conftest import auth_headers


def _csv(text: str, name: str = "catalogo.csv"):
    return {"file": (name, io.BytesIO(text.encode("utf-8")), "text/csv")}


def _tree(client, headers):
    """CCTV > (Cámaras IP, NVR, Discos Duros, Otros) y Cableado > Otros: "Otros" queda repetido a propósito."""
    def make(name, parent=None, prefix=None):
        payload = {"name": name, "code_prefix": prefix}
        if parent:
            payload["parent_id"] = parent["id"]
        resp = client.post("/api/categories", json=payload, headers=headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    cctv = make("CCTV")
    cableado = make("Cableado")
    for name, prefix in [("Cámaras IP", "CAM"), ("NVR", "NVR"), ("Discos Duros", "DSK"), ("Otros", None)]:
        make(name, cctv, prefix)
    make("Otros", cableado)


def test_parse_number_accepts_dominican_and_spanish_formats():
    assert parse_number("1250") == 1250
    assert parse_number("1,250.50") == 1250.5
    assert parse_number("1.250,50") == 1250.5
    assert parse_number("RD$ 3,500") == 3500
    assert parse_number("3500,5") == 3500.5
    assert parse_number("0.75") == 0.75


def test_template_has_excel_separator_hint_and_examples():
    text = template_csv().decode("utf-8")
    assert text.lstrip("﻿").startswith("sep=;")
    assert "EJEMPLO" in text and "Nombre;Categoria" in text


def test_dry_run_changes_nothing_and_reports_the_plan(client, admin_token):
    headers = auth_headers(admin_token)
    _tree(client, headers)
    before = len(client.get("/api/catalog", headers=headers).json())
    body = (
        "Nombre;Categoria;Unidad;Precio;Marca;Etiquetas\n"
        'Cámara IP 4MP Hikvision;Cámaras IP;unidad;3.500,00;Hikvision;"camara;ip;4mp"\n'
        "Disco duro 4TB;Discos Duros;unidad;RD$ 5,200;Seagate;disco;almacenamiento\n"
    )
    resp = client.post("/api/catalog/import?dry_run=true", files=_csv(body), headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["dry_run"] is True
    assert data["created"] == 2 and data["errors"] == 0
    assert len(client.get("/api/catalog", headers=headers).json()) == before


def test_import_creates_updates_and_never_erases_with_empty_cells(client, admin_token):
    headers = auth_headers(admin_token)
    _tree(client, headers)
    body = (
        "sep=;\n"
        "Nombre;Categoria;Unidad;Precio;Costo;Marca;Etiquetas;Sinonimos\n"
        "EJEMPLO fila de la plantilla;Cámaras IP;unidad;1;;;;\n"
        'Cámara IP 4MP;Cámaras IP;unidad;3500;2400;Hikvision;"camara;ip;4mp";"camara 4 megapixeles"\n'
        "NVR 32 canales;NVR;unidad;18000;;;nvr;\n"
    )
    resp = client.post("/api/catalog/import?dry_run=false", files=_csv(body), headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert (data["created"], data["updated"], data["skipped"], data["errors"]) == (2, 0, 1, 0)

    products = {p["name"]: p for p in client.get("/api/catalog", headers=headers).json()}
    camera = products["Cámara IP 4MP"]
    assert camera["price"] == 3500 and camera["cost"] == 2400 and camera["brand"] == "Hikvision"
    assert camera["code"].startswith("CAM") or camera["code"]  # código generado
    assert "camara 4 megapixeles" in camera["synonyms"]
    assert "EJEMPLO fila de la plantilla" not in products

    # Segunda carga: mismo nombre -> actualiza el precio; la marca queda porque la celda viene vacía.
    again = "Nombre;Precio;Marca\nCámara IP 4MP;3800;\n"
    resp = client.post("/api/catalog/import?dry_run=false", files=_csv(again), headers=headers)
    assert resp.status_code == 200, resp.text
    assert (resp.json()["created"], resp.json()["updated"]) == (0, 1)
    updated = {p["name"]: p for p in client.get("/api/catalog", headers=headers).json()}["Cámara IP 4MP"]
    assert updated["price"] == 3800
    assert updated["brand"] == "Hikvision"  # no se borró
    assert updated["code"] == camera["code"]  # mismo producto, sin duplicar

    # Se puede apuntar por código aunque cambie el nombre.
    by_code = f"Codigo;Nombre;Precio\n{camera['code']};Cámara IP 4MP bala;3900\n"
    resp = client.post("/api/catalog/import?dry_run=false", files=_csv(by_code), headers=headers)
    assert resp.json()["updated"] == 1
    renamed = [p for p in client.get("/api/catalog", headers=headers).json() if p["code"] == camera["code"]][0]
    assert renamed["name"] == "Cámara IP 4MP bala" and renamed["price"] == 3900


def test_row_errors_are_reported_without_blocking_the_rest(client, admin_token):
    headers = auth_headers(admin_token)
    _tree(client, headers)
    body = (
        "Nombre;Categoria;Precio\n"
        "Producto bueno;Cámaras IP;100\n"
        "Producto sin categoria;;100\n"
        "Producto categoria inventada;Zzz;100\n"
        "Producto precio malo;Cámaras IP;mucho\n"
        ";Cámaras IP;5\n"
    )
    resp = client.post("/api/catalog/import?dry_run=false", files=_csv(body), headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["created"] == 1 and data["errors"] == 4
    messages = {r["row"]: r["message"] for r in data["rows"] if r["action"] == "error"}
    assert "categoría" in messages[3]
    assert "no existe" in messages[4]
    assert "número" in messages[5]
    assert "nombre" in messages[6]


def test_ambiguous_category_asks_for_the_full_path(client, admin_token):
    headers = auth_headers(admin_token)
    _tree(client, headers)
    body = (
        "Nombre;Categoria;Precio\n"
        "Algo;Otros;1\n"
        "Algo 2;Cableado > Otros;2\n"
        "Algo 3;cctv > otros;3\n"
    )

    data = client.post("/api/catalog/import?dry_run=true", files=_csv(body), headers=headers).json()

    assert data["errors"] == 1 and data["created"] == 2
    assert "ruta completa" in data["rows"][0]["message"]


def test_bad_files_and_permissions(client, admin_token, oficina_token, tecnico_token):
    headers = auth_headers(admin_token)
    no_name = client.post("/api/catalog/import", files=_csv("Precio;Marca\n1;x\n"), headers=headers)
    assert no_name.status_code == 400 and "Nombre" in no_name.json()["detail"]
    empty = client.post("/api/catalog/import", files=_csv("   \n"), headers=headers)
    assert empty.status_code == 400

    # Crear productos es de admin, igual que POST /api/catalog.
    assert client.post("/api/catalog/import", files=_csv("Nombre\nx\n"), headers=auth_headers(oficina_token)).status_code == 403
    assert client.post("/api/catalog/import", files=_csv("Nombre\nx\n"), headers=auth_headers(tecnico_token)).status_code == 403
    # La plantilla la pueden bajar admin y oficina, no el técnico.
    assert client.get("/api/catalog/import-template", headers=auth_headers(oficina_token)).status_code == 200
    assert client.get("/api/catalog/import-template", headers=auth_headers(tecnico_token)).status_code == 403
