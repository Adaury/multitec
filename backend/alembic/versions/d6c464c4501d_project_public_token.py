"""project public token

Revision ID: d6c464c4501d
Revises: 85d49b0ed93a
Create Date: 2026-07-03 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6c464c4501d'
down_revision: Union[str, None] = '85d49b0ed93a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add_column simple (sin CONSTRAINT nuevo aparte del UNIQUE, que sí necesita batch en
    # SQLite) — igual que la lección de la migración de NCF, separamos por dialecto.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table('projects', recreate='always') as batch_op:
            batch_op.add_column(sa.Column('public_token', sa.String(length=64), nullable=True))
            batch_op.create_unique_constraint('uq_projects_public_token', ['public_token'])
    else:
        op.add_column('projects', sa.Column('public_token', sa.String(length=64), nullable=True))
        op.create_unique_constraint('uq_projects_public_token', 'projects', ['public_token'])


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table('projects', recreate='always') as batch_op:
            batch_op.drop_constraint('uq_projects_public_token', type_='unique')
            batch_op.drop_column('public_token')
    else:
        op.drop_constraint('uq_projects_public_token', 'projects', type_='unique')
        op.drop_column('projects', 'public_token')
