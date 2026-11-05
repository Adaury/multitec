import io

from openpyxl import Workbook, load_workbook

from tests.conftest import auth_headers, make_project


def _xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    for row in rows:
        wb.active.append(row)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def test_catalog_templates_for_alarm_and_hardware_download_as_excel(client, admin_token):
    h = auth_headers(admin_token)
    for kind in ("alarma", "ferreteria", "general"):
        res = client.get("/api/catalog/import-template", params={"kind": kind, "format": "xlsx"}, headers=h)
        assert res.status_code == 200
        sheet = load_workbook(io.BytesIO(res.content)).active
        assert sheet.cell(1, 1).value == "Nombre" and sheet.max_row > 2


def test_several_excel_and_csv_files_import_at_once_creating_missing_categories(client, admin_token):
    h = auth_headers(admin_token)
    alarm = _xlsx([["Nombre", "Categoria", "Unidad", "Precio"], ["Sirena exterior con estrobo", "Alarmas > Sirenas", "unidad", 1850]])
    hardware = "Nombre;Categoria;Precio\nTaco plástico 1/4;Ferretería > Anclajes;\n".encode("utf-8")
    files = [
        ("files", ("alarma.xlsx", alarm, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("files", ("ferreteria.csv", hardware, "text/csv")),
    ]

    preview = client.post("/api/catalog/import", params={"create_categories": True}, files=files, headers=h).json()
    assert preview["dry_run"] and preview["created"] == 2 and preview["errors"] == 0
    assert set(preview["new_categories"]) == {"Alarmas", "Alarmas > Sirenas", "Ferretería", "Ferretería > Anclajes"}
    assert {r["file"] for r in preview["rows"]} == {"alarma.xlsx", "ferreteria.csv"}
    assert not [p for p in client.get("/api/catalog", headers=h).json() if p["name"] == "Sirena exterior con estrobo"]

    done = client.post("/api/catalog/import", params={"create_categories": True, "dry_run": False}, files=files, headers=h).json()
    assert done["created"] == 2
    catalog = {p["name"]: p for p in client.get("/api/catalog", headers=h).json()}
    assert catalog["Sirena exterior con estrobo"]["price"] == 1850
    assert catalog["Taco plástico 1/4"]["price"] == 0 and catalog["Taco plástico 1/4"]["price_estimated"] is True

    # Sin permiso de crear categorías, una que no existe sigue siendo un error.
    other = [("files", ("x.csv", "Nombre;Categoria\nCosa;Categoria Inventada\n".encode(), "text/csv"))]
    assert client.post("/api/catalog/import", files=other, headers=h).json()["errors"] == 1


def test_catalog_export_can_be_uploaded_back_to_update(client, admin_token):
    h = auth_headers(admin_token)
    client.post("/api/catalog/import", params={"create_categories": True, "dry_run": False},
                files=[("files", ("a.csv", "Nombre;Categoria;Precio\nPanel de alarma 8 zonas;Alarmas > Paneles;9000\n".encode(), "text/csv"))],
                headers=h)
    exported = client.get("/api/catalog/export", params={"format": "xlsx"}, headers=h)
    sheet = load_workbook(io.BytesIO(exported.content)).active
    rows = list(sheet.iter_rows(values_only=True))
    panel = next(r for r in rows if r[0] == "Panel de alarma 8 zonas")
    assert panel[1] == "Alarmas > Paneles" and panel[10]

    edited = [list(rows[0]), [*panel[:3], 9500, *panel[4:]]]
    res = client.post("/api/catalog/import", params={"dry_run": False}, files=[("files", ("c.xlsx", _xlsx(edited), "application/octet-stream"))], headers=h).json()
    assert res["updated"] == 1 and res["created"] == 0
    assert next(p for p in client.get("/api/catalog", headers=h).json() if p["name"] == "Panel de alarma 8 zonas")["price"] == 9500


def test_quote_items_download_and_load_back(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    budget = client.post(f"/api/projects/{project['id']}/budgets", json={"items": [{"description": "Cámara IP", "quantity": 2, "unit_price": 500}]}, headers=h).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=h).json()

    file = client.get(f"/api/quotes/{quote['id']}/items-file", params={"format": "xlsx"}, headers=h)
    assert file.status_code == 200
    parsed = client.post("/api/line-items/parse", files=[("files", ("cot.xlsx", file.content, "application/octet-stream"))], headers=h).json()
    # Las filas de Subtotal / ITBIS / TOTAL del archivo descargado no vuelven como partidas.
    assert [(i["description"], i["quantity"], i["unit_price"]) for i in parsed["items"]] == [("Cámara IP", 2, 500)]

    csv = "Descripcion;Cantidad;Precio\nSensor PIR;3;\nAmarres;1;150\n".encode()
    two = client.post("/api/line-items/parse", files=[("files", ("a.csv", csv, "text/csv")), ("files", ("b.xlsx", file.content, "application/octet-stream"))], headers=h).json()
    assert len(two["items"]) == 3
    assert any("Sensor PIR" in w for w in two["warnings"])


def test_technician_cannot_use_catalog_or_quote_files(client, tecnico_token):
    h = auth_headers(tecnico_token)
    assert client.get("/api/catalog/export", headers=h).status_code == 403
    assert client.post("/api/line-items/parse", files=[("files", ("a.csv", b"Descripcion\nX\n", "text/csv"))], headers=h).status_code == 403
