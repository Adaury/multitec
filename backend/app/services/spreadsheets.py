"""Leer y escribir hojas de cálculo para importar y exportar (catálogo, partidas de cotización).

Se aceptan los dos formatos que la gente tiene a mano: CSV (el «Guardar como CSV» de Excel, con `;` o `,`)
y Excel (.xlsx). Lo que se lee sale siempre como filas de texto, para que el resto del código no tenga que
saber de dónde vino el archivo.
"""

import csv
import io
import zipfile
from datetime import date, datetime

from app.services.csv_export import _safe_cell

MAX_BYTES = 2 * 1024 * 1024
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _is_xlsx(data: bytes, filename: str | None) -> bool:
    # Un .xlsx es un ZIP; se mira el contenido y no solo el nombre (un CSV renombrado no se cuela).
    return data[:4] == b"PK\x03\x04" and (filename is None or not filename.lower().endswith(".csv"))


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, float):
        # 3500.0 -> "3500"; 12.5 -> "12.5" (sin notación científica ni ceros de más)
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def _csv_rows(data: bytes) -> list[list[str]]:
    text = _decode(data)
    lines = text.splitlines()
    delimiter = None
    if lines and lines[0].strip().lower().startswith("sep=") and len(lines[0].strip()) >= 5:
        delimiter = lines[0].strip()[4]
        lines = lines[1:]
    if not any(line.strip() for line in lines):
        return []
    if delimiter is None:
        first = next(line for line in lines if line.strip())
        delimiter = max([";", ",", "\t"], key=first.count)
    return [list(row) for row in csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)]


def _xlsx_rows(data: bytes) -> list[list[str]]:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise ValueError("El archivo de Excel está dañado o no es un .xlsx") from exc
    try:
        sheet = workbook.worksheets[0]
        return [[_cell_text(v) for v in row] for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def read_rows(data: bytes, filename: str | None = None) -> list[list[str]]:
    """Filas de texto de un CSV o de la primera hoja de un Excel. Las filas vacías del final se quitan."""
    if len(data) > MAX_BYTES:
        raise ValueError(f"El archivo pesa más de {MAX_BYTES // (1024 * 1024)} MB")
    if filename and filename.lower().endswith(".xls"):
        raise ValueError("El formato .xls (Excel viejo) no se puede leer: guárdalo como .xlsx o CSV")
    rows = _xlsx_rows(data) if _is_xlsx(data, filename) else _csv_rows(data)
    while rows and not any(c.strip() for c in rows[-1]):
        rows.pop()
    return rows


def build_xlsx(headers: list[str], rows: list[list], sheet_title: str = "Hoja1", widths: list[int] | None = None) -> bytes:
    """Excel con el encabezado en negrita y fijo arriba. Los textos que Excel tomaría por fórmula se
    neutralizan igual que en los CSV."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title[:31]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0A63E2")
    for row in rows:
        sheet.append([_safe_cell(v) for v in row])
    sheet.freeze_panes = "A2"
    for index, header in enumerate(headers, start=1):
        width = (widths[index - 1] if widths and index - 1 < len(widths) else None) or max(12, min(45, len(header) + 4))
        sheet.column_dimensions[sheet.cell(row=1, column=index).column_letter].width = width
    out = io.BytesIO()
    workbook.save(out)
    return out.getvalue()


def build_csv_semicolon(headers: list[str], rows: list[list]) -> bytes:
    """CSV con `sep=;` (Excel lo abre en columnas con cualquier configuración regional) y BOM UTF-8."""
    out = io.StringIO()
    out.write("sep=;\r\n")
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_cell(v) for v in row])
    return ("﻿" + out.getvalue()).encode("utf-8")
