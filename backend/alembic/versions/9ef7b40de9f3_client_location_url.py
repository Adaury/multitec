"""client location_url

Revision ID: 9ef7b40de9f3
Revises: eccc613fdde1
Create Date: 2026-07-07 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ef7b40de9f3'
down_revision: Union[str, None] = 'eccc613fdde1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('location_url', sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'location_url')
