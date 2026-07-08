"""budget_items note

Revision ID: c4d92f8a1b3e
Revises: b3a1c7e2f4d6
Create Date: 2026-07-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d92f8a1b3e'
down_revision: Union[str, None] = 'b3a1c7e2f4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('budget_items', sa.Column('note', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('budget_items', 'note')
