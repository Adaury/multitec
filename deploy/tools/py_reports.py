"""Genera con el sistema ORIGINAL (Python + PostgreSQL real) los reportes que luego se comparan con Laravel.
SOLO LECTURA (PGOPTIONS fuerza la transacción de solo lectura). Salida: carpeta del argumento 1.
"""
import json
import os
import sys
from pathlib import Path

os.environ["PGOPTIONS"] = "-c default_transaction_read_only=on"
BACKEND = r"C:\laragon\www\multitec\backend"
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

from app.db.session import SessionLocal  # noqa: E402
from app.models.invoice import Invoice  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.quote import Quote  # noqa: E402
from app.services.dgii_606 import build_606_report  # noqa: E402
from app.services.dgii_607 import build_607_consumption_summary, build_607_report  # noqa: E402
from app.services.dgii_608 import build_608_report  # noqa: E402
from app.services.followups import build_followups  # noqa: E402
from app.services.margin import company_margin_last_months, project_margin  # noqa: E402
from app.services.margin import compute_margin  # noqa: E402

with SessionLocal(company_id=1) as db:
    for year in (2025, 2026):
        for month in range(1, 13):
            tag = f"{year}{month:02d}"
            (out / f"606_{tag}.csv").write_bytes(build_606_report(db, year, month))
            (out / f"607_{tag}.csv").write_bytes(build_607_report(db, year, month))
            (out / f"608_{tag}.csv").write_bytes(build_608_report(db, year, month))
            (out / f"607resumen_{tag}.json").write_text(json.dumps(build_607_consumption_summary(db, year, month)), encoding="utf-8")
    (out / "margen_empresa.json").write_text(json.dumps(company_margin_last_months(db)), encoding="utf-8")
    margins = {str(p.id): project_margin(db, p.id) for p in db.query(Project).all()}
    (out / "margen_proyectos.json").write_text(json.dumps(margins), encoding="utf-8")
    qm = {str(q.id): compute_margin(db, q.items, basis="cotizado") for q in db.query(Quote).all()}
    (out / "margen_cotizaciones.json").write_text(json.dumps(qm), encoding="utf-8")
    im = {str(i.id): compute_margin(db, i.items, basis="facturado") for i in db.query(Invoice).all()}
    (out / "margen_facturas.json").write_text(json.dumps(im), encoding="utf-8")
    (out / "seguimientos.json").write_text(json.dumps(build_followups(db).model_dump(mode="json")), encoding="utf-8")
print("listo ->", out)
