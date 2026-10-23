"""product price_estimated (precio de ejemplo por confirmar)

Revision ID: e5b9c4d7f1a3
Revises: d4a8b3c6e2f5
Create Date: 2026-10-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b9c4d7f1a3'
down_revision: Union[str, None] = 'd4a8b3c6e2f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('price_estimated', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column('products', 'price_estimated')
