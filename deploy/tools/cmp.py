import json
import sys
from pathlib import Path

a, b = Path(sys.argv[1]), Path(sys.argv[2])


def eq(x, y, path=""):
    """Igualdad estructural; los números se comparan con tolerancia de redondeo (1e-9); devuelve la primera diferencia."""
    if isinstance(x, dict) and isinstance(y, dict):
        if set(x) != set(y):
            return f"{path}: claves distintas {sorted(set(x) ^ set(y))}"
        for k in x:
            r = eq(x[k], y[k], f"{path}/{k}")
            if r:
                return r
        return None
    if isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            return f"{path}: largo {len(x)} vs {len(y)}"
        for i, (p, q) in enumerate(zip(x, y)):
            r = eq(p, q, f"{path}[{i}]")
            if r:
                return r
        return None
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
        return None if abs(x - y) < 1e-9 else f"{path}: {x} vs {y}"
    if isinstance(x, str) and isinstance(y, str):
        # fechas ISO: Python 2026-11-18T14:57:05 vs Laravel 2026-11-18T14:57:05.000000Z -> se comparan hasta el segundo
        if len(x) >= 19 and x[:19] == y[:19] and x[10:11] == "T":
            return None
    return None if x == y else f"{path}: {x!r} vs {y!r}"


files = sorted(p.name for p in a.iterdir())
ok = bad = 0
detail = []
con_datos = []
for name in files:
    pa, pb = a / name, b / name
    if not pb.exists():
        bad += 1
        detail.append(f"{name}: falta en Laravel")
        continue
    if name.endswith(".csv"):
        same = pa.read_bytes() == pb.read_bytes()
        rows = max(0, len(pa.read_text(encoding="utf-8-sig").splitlines()) - 1)
        if rows:
            con_datos.append(f"{name} ({rows} fila(s))")
        diff = None if same else "contenido distinto"
    else:
        diff = eq(json.loads(pa.read_text(encoding="utf-8")), json.loads(pb.read_text(encoding="utf-8")))
    if diff:
        bad += 1
        detail.append(f"{name}: {diff}")
    else:
        ok += 1
print(f"{ok} archivos IDENTICOS, {bad} con diferencias, de {len(files)}")
print("Reportes DGII con datos:", ", ".join(con_datos) or "(ninguno)")
for d in detail[:15]:
    print("  X", d.encode("ascii", "replace").decode())
sys.exit(1 if bad else 0)  # el script de migración se detiene si algo no coincide
