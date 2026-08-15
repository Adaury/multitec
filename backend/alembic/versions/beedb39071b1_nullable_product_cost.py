"""nullable product cost

Revision ID: beedb39071b1
Revises: a3f6c9d21b7e
Create Date: 2026-08-15 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'beedb39071b1'
down_revision: Union[str, None] = 'a3f6c9d21b7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NULL ahora significa "sin costo cargado", distinto de un costo real de $0 (ej. un
    # artículo de regalo) — ver services/margin.py. Antes de este cambio, 0 hacía ambos
    # trabajos a la vez, así que las filas existentes en 0 son indistinguibles de "nunca se
    # cargó" y se migran a NULL para preservar su comportamiento actual (excluidas de
    # `lines_costed`).
    # Modo 'auto' (no 'always'): en Postgres esto es un ALTER COLUMN nativo, sin recrear la
    # tabla — recrearla arrastraría las FKs de budget_items/quote_items/etc. contra
    # products.id. Solo SQLite (que no soporta ALTER COLUMN) fuerza una recreación aquí.
    with op.batch_alter_table('products') as batch_op:
        batch_op.alter_column('cost', existing_type=sa.Numeric(12, 2), nullable=True, server_default=None)
    op.execute("UPDATE products SET cost = NULL WHERE cost = 0")


def downgrade() -> None:
    op.execute("UPDATE products SET cost = 0 WHERE cost IS NULL")
    with op.batch_alter_table('products') as batch_op:
        batch_op.alter_column('cost', existing_type=sa.Numeric(12, 2), nullable=False, server_default='0')
