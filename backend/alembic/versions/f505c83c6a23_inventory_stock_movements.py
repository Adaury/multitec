"""inventory stock movements

Revision ID: f505c83c6a23
Revises: cdbaf1a4b580
Create Date: 2026-07-03 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f505c83c6a23'
down_revision: Union[str, None] = 'cdbaf1a4b580'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add_column simple (sin CONSTRAINT nuevo) funciona nativo en SQLite y Postgres, no
    # hace falta batch mode aquí — a diferencia de agregar una FK o UNIQUE después.
    op.add_column('products', sa.Column('stock_quantity', sa.Numeric(12, 2), server_default='0', nullable=False))

    op.create_table(
        'stock_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('movement_type', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False
        ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('stock_movements')
    op.drop_column('products', 'stock_quantity')
