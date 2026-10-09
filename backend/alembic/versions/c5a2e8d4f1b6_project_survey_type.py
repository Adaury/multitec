"""project survey_type

Revision ID: c5a2e8d4f1b6
Revises: b7e4d1c9a2f3
Create Date: 2026-10-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5a2e8d4f1b6'
down_revision: Union[str, None] = 'b7e4d1c9a2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columna nullable sin FK: ALTER TABLE ADD COLUMN simple, funciona igual en SQLite y PostgreSQL.
    op.add_column('projects', sa.Column('survey_type', sa.String(length=60), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_column('survey_type')
