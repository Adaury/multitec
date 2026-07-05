"""product_storage_fields

Revision ID: 71cc131c407a
Revises: 21847344e44d
Create Date: 2026-07-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71cc131c407a'
down_revision: Union[str, None] = '21847344e44d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Motor 5/StorageCalculator (§ docs/ai-engine-architecture.md) — resolución de cámara
    # y capacidad de almacenamiento, los dos datos que le faltaban a Motor 2 para poder
    # estimar espacio en disco. Ambos nullable, sin default: un producto que no es cámara
    # ni almacenamiento simplemente no participa del cálculo. Aditivo puro, no hace falta
    # batch mode ni en SQLite.
    op.add_column('products', sa.Column('resolution_mp', sa.Numeric(6, 2), nullable=True))
    op.add_column('products', sa.Column('storage_capacity_gb', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'storage_capacity_gb')
    op.drop_column('products', 'resolution_mp')
