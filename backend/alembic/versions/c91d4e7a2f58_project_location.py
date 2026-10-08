"""project location

Revision ID: c91d4e7a2f58
Revises: beedb39071b1
Create Date: 2026-10-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c91d4e7a2f58'
down_revision: Union[str, None] = 'beedb39071b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Un cliente puede tener varias obras en sitios distintos: la ubicación de cada proyecto
    # va en el proyecto, y la del cliente queda como respaldo cuando el proyecto no tiene.
    # Ambas columnas son NULL-ables, así que las filas existentes no cambian.
    op.add_column('projects', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('location_url', sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'location_url')
    op.drop_column('projects', 'address')
