"""user must_change_password

Revision ID: f7a3c1e9b2d4
Revises: e4c7a9b2d5f1
Create Date: 2026-10-10 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a3c1e9b2d4'
down_revision: Union[str, None] = 'e4c7a9b2d5f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default false: los usuarios existentes siguen entrando sin que nada los bloquee.
    op.add_column(
        'users',
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('must_change_password')
