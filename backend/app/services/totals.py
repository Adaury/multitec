from dataclasses import dataclass


@dataclass
class LineInput:
    quantity: float
    unit_price: float


def line_subtotal(quantity: float, unit_price: float) -> float:
    return round(float(quantity) * float(unit_price), 2)


def compute_totals(items: list[LineInput], itbis_rate: float) -> tuple[float, float, float]:
    """Devuelve (subtotal, itbis, total) a partir de una lista de líneas."""
    subtotal = round(sum(line_subtotal(item.quantity, item.unit_price) for item in items), 2)
    itbis = round(subtotal * itbis_rate, 2)
    total = round(subtotal + itbis, 2)
    return subtotal, itbis, total
