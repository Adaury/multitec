"""product_channel_capacity

Revision ID: 4abec1ec6eff
Revises: 71cc131c407a
Create Date: 2026-07-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4abec1ec6eff'
down_revision: Union[str, None] = '71cc131c407a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Motor 5/CapacityCalculator (§ docs/ai-engine-architecture.md) — canales de NVR o
    # puertos de switch disponibles. Un solo campo para ambos: son el mismo concepto
    # ("cuántos dispositivos puede recibir este hub"). Nullable, aditivo puro, no hace
    # falta batch mode ni en SQLite.
    op.add_column('products', sa.Column('channel_capacity', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'channel_capacity')
