"""Exporta la base REAL de Multitec (PostgreSQL) a archivos JSON-lines, una tabla por archivo.

SOLO LECTURA: la sesión se abre con default_transaction_read_only=on, así que ni por error puede escribir.
Salida: la carpeta que se pasa como argumento (fuera de la web y de git). Contiene datos reales de clientes.
Fechas con hora -> UTC 'YYYY-MM-DD HH:MM:SS'; fechas -> 'YYYY-MM-DD'; decimales -> texto exacto (sin pasar por float).
"""
import base64
import datetime as dt
import decimal
import json
import re
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

ENV = r"C:\laragon\www\multitec\backend\.env"
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

url = next(m.group(1) for line in open(ENV, encoding="utf-8") if (m := re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)))
engine = create_engine(
    url.replace("+psycopg2", "+psycopg"), connect_args={"options": "-c default_transaction_read_only=on"}
)


def conv(v):
    if isinstance(v, dt.datetime):
        if v.tzinfo is not None:
            v = v.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return v.strftime("%Y-%m-%d %H:%M:%S")  # TIMESTAMP sin zona: ya está en UTC en este sistema
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, dt.time):
        return v.strftime("%H:%M:%S")
    if isinstance(v, decimal.Decimal):
        return format(v, "f")
    if isinstance(v, (bytes, memoryview)):
        return {"__b64__": base64.b64encode(bytes(v)).decode()}
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


insp = inspect(engine)
summary = []
with engine.connect() as c:
    assert c.execute(text("SHOW default_transaction_read_only")).scalar() == "on", "la sesión NO es de solo lectura"
    for table in sorted(insp.get_table_names()):
        cols = [col["name"] for col in insp.get_columns(table)]
        order = "id" if "id" in cols else f'"{cols[0]}"'  # una sola columna simple: algunas tablas tienen JSON
        rows = c.execute(text(f'SELECT * FROM "{table}" ORDER BY {order}')).mappings().all()
        with open(out / f"{table}.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps({k: conv(r[k]) for k in cols}, ensure_ascii=False) + "\n")
        summary.append({"table": table, "rows": len(rows), "columns": cols})
json.dump(summary, open(out / "_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("exportadas", len(summary), "tablas,", sum(s["rows"] for s in summary), "filas ->", out)
