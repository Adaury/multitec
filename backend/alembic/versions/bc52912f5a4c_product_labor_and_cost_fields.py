"""product_labor_and_cost_fields

Revision ID: bc52912f5a4c
Revises: 0e5678a24560
Create Date: 2026-07-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc52912f5a4c'
down_revision: Union[str, None] = '0e5678a24560'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Motor 2 (§ docs/ai-engine-architecture.md) — campos que faltaban frente al objetivo
    # del catálogo inteligente: costo (distinto del precio de venta) y los insumos que
    # necesitará Motor 5/LaborCalculator (tiempo de instalación, rol de mano de obra,
    # prioridad). Todo aditivo con default o nullable, no hace falta batch mode ni en
    # SQLite — mismo patrón que products.stock_quantity.
    op.add_column('products', sa.Column('cost', sa.Numeric(12, 2), server_default='0', nullable=False))
    op.add_column('products', sa.Column('install_minutes', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('labor_role', sa.String(length=80), nullable=True))
    op.add_column('products', sa.Column('priority', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'priority')
    op.drop_column('products', 'labor_role')
    op.drop_column('products', 'install_minutes')
    op.drop_column('products', 'cost')
