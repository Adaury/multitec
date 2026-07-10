from pydantic import BaseModel


class MarginSummary(BaseModel):
    """Venta/costo/margen calculados en vivo contra `Product.cost` actual — sin snapshot
    histórico por línea (§ plan de rentabilidad). `margin_pct` es None si `revenue == 0`.
    `lines_costed < lines_total` señala que el margen es parcial (hay líneas sin producto
    de catálogo o con costo sin cargar)."""

    revenue: float
    cost: float
    margin: float
    margin_pct: float | None
    lines_total: int
    lines_costed: int
    basis: str
