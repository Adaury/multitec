"""Pone un precio de EJEMPLO a los productos del catálogo que tienen precio 0.

Uso (desde la carpeta backend):

    venv/Scripts/python.exe scripts/estimate_prices.py          # solo muestra qué haría
    venv/Scripts/python.exe scripts/estimate_prices.py --apply  # lo aplica
    ... --company 2                                             # otra empresa (por defecto la 1, Multitec)

Regla: si el producto tiene costo, precio = costo + 35 %; si no, un precio típico según el prefijo
de su categoría (RD$). Los productos quedan marcados como `price_estimated` (el catálogo los
señala) hasta que alguien confirme el precio.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models.product import Product, resolve_code_prefix  # noqa: E402

MARKUP = 1.35
FALLBACK_PRICE = 500.0
TYPICAL_PRICE_BY_PREFIX = {
    "CAM": 4500.0,
    "NVR": 12000.0,
    "DVR": 8500.0,
    "DD": 5500.0,
    "MON": 7500.0,
    "FTE": 650.0,
    "CAB": 25.0,
    "CND": 90.0,
    "CNX": 60.0,
    "RED": 3500.0,
    "SW": 6500.0,
    "FO": 1800.0,
    "ACC": 350.0,
    "VP": 5500.0,
    "AUT": 18000.0,
    "BAR": 45000.0,
    "HER": 1200.0,
}


def estimate(product: Product) -> float:
    if product.cost:
        return round(float(product.cost) * MARKUP, 2)
    return TYPICAL_PRICE_BY_PREFIX.get(resolve_code_prefix(product.category), FALLBACK_PRICE)


def main() -> None:
    apply = "--apply" in sys.argv
    company_id = int(sys.argv[sys.argv.index("--company") + 1]) if "--company" in sys.argv else 1
    with SessionLocal(company_id=company_id) as db:
        products = db.query(Product).filter(Product.price == 0).order_by(Product.code).all()
        for product in products:
            price = estimate(product)
            print(f"{product.code:12} {product.name[:45]:45} -> RD$ {price:,.2f}")
            if apply:
                product.price = price
                product.price_estimated = True
        if apply:
            db.commit()
        print(f"\n{len(products)} producto(s) con precio 0." + ("" if apply else " Usa --apply para guardarlos."))


if __name__ == "__main__":
    main()
