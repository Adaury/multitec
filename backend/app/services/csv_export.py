import csv
from io import StringIO

UTF8_BOM = "﻿"


def build_csv(headers: list[str], rows: list[list]) -> bytes:
    """Arma un CSV con BOM UTF-8 — sin el BOM, Excel en Windows (el uso más común aquí)
    interpreta mal los acentos y la ñ al abrir el archivo directamente."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return (UTF8_BOM + buf.getvalue()).encode("utf-8")
