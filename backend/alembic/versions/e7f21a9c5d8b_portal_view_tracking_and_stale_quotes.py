"""portal view tracking and stale quote reminders

Revision ID: e7f21a9c5d8b
Revises: c4d92f8a1b3e
Create Date: 2026-07-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f21a9c5d8b'
down_revision: Union[str, None] = 'c4d92f8a1b3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('portal_first_viewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('projects', sa.Column('portal_last_viewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quotes', sa.Column('stale_notified', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('quotes', 'stale_notified')
    op.drop_column('projects', 'portal_last_viewed_at')
    op.drop_column('projects', 'portal_first_viewed_at')
