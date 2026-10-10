"""user assistant_alias

Revision ID: d9b3f6a1c4e8
Revises: c5a2e8d4f1b6
Create Date: 2026-10-09 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9b3f6a1c4e8'
down_revision: Union[str, None] = 'c5a2e8d4f1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columna nullable sin FK: ALTER TABLE ADD COLUMN simple, igual en SQLite y PostgreSQL.
    op.add_column('users', sa.Column('assistant_alias', sa.String(length=60), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('assistant_alias')
