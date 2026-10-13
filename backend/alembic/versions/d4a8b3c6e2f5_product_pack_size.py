"""product pack size (unidades por paquete)

Revision ID: d4a8b3c6e2f5
Revises: c3f7a2b8d4e1
Create Date: 2026-10-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a8b3c6e2f5'
down_revision: Union[str, None] = 'c3f7a2b8d4e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nulo = se vende por unidad: el catálogo existente no cambia de comportamiento.
    op.add_column('products', sa.Column('pack_size', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_column('pack_size')
