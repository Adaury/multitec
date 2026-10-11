"""invoice payment method and retentions (607)

Revision ID: e4c7a9b2d5f1
Revises: d9b3f6a1c4e8
Create Date: 2026-10-10 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4c7a9b2d5f1'
down_revision: Union[str, None] = 'd9b3f6a1c4e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columnas nuevas sin FK: ALTER TABLE ADD COLUMN simple en SQLite y PostgreSQL. Las numéricas
    # llevan server_default para que las facturas ya existentes queden en 0 (sin retención).
    op.add_column('invoices', sa.Column('payment_method', sa.String(length=20), nullable=True))
    op.add_column('invoices', sa.Column('itbis_withheld', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('invoices', sa.Column('isr_withheld', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('invoices', sa.Column('retention_date', sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.drop_column('retention_date')
        batch_op.drop_column('isr_withheld')
        batch_op.drop_column('itbis_withheld')
        batch_op.drop_column('payment_method')
