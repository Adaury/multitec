"""purchase invoice isr retention type (606, columna 17)

Revision ID: c3f7a2b8d4e1
Revises: b2e6f1a7c3d9
Create Date: 2026-10-12 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f7a2b8d4e1'
down_revision: Union[str, None] = 'b2e6f1a7c3d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: las facturas de compra ya registradas no tienen tipo y no se inventa uno.
    op.add_column('purchase_invoices', sa.Column('isr_retention_type', sa.String(length=2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('purchase_invoices') as batch_op:
        batch_op.drop_column('isr_retention_type')
