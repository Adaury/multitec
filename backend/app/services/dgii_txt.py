"""Archivo de envío de la DGII (606/607/608): texto delimitado por "|", una línea de
encabezado `FORMATO|RNC|AAAAMM|CANTIDAD` y luego un registro por línea, sin títulos de columna.
El CSV de los reportes sirve para revisar en Excel; este es el que se carga en la Oficina Virtual."""

from fastapi import HTTPException


def _cell(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace("|", " ").replace("\r", " ").replace("\n", " ").strip()


def company_rnc_digits(raw: str) -> str:
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) not in (9, 11):
        raise HTTPException(
            status_code=400,
            detail=(
                "Para generar el archivo de la DGII hace falta el RNC de la empresa (9 u 11 dígitos). "
                "Escríbelo en «Mi empresa» (campo RNC)."
            ),
        )
    return digits


def build_dgii_txt(form: str, company_rnc: str, year: int, month: int, rows: list[list]) -> bytes:
    rnc = company_rnc_digits(company_rnc)
    lines = [f"{form}|{rnc}|{year:04d}{month:02d}|{len(rows)}"]
    lines.extend("|".join(_cell(value) for value in row) for row in rows)
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")
