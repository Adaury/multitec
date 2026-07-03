"""user audit columns

Revision ID: 24f27f0269fc
Revises: 093cf2d8eda3
Create Date: 2026-07-02 23:11:27.598855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24f27f0269fc'
down_revision: Union[str, None] = '093cf2d8eda3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # recreate='always': ver nota en 093cf2d8eda3 (evita CircularDependencyError en SQLite).
    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                'created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False
            )
        )
        batch_op.create_foreign_key('fk_users_created_by_users', 'users', ['created_by'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.drop_constraint('fk_users_created_by_users', type_='foreignkey')
        batch_op.drop_column('created_at')
        batch_op.drop_column('created_by')
