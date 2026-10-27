"""empresas: periodo de prueba, tope de usuarios y marca de demo

Revision ID: e1b5c8d2f4a6
Revises: d9a4b7c2e1f3
Create Date: 2026-10-26
"""

import sqlalchemy as sa
from alembic import op

revision = 'e1b5c8d2f4a6'
down_revision = 'd9a4b7c2e1f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('companies', sa.Column('max_users', sa.Integer(), nullable=True))
    op.add_column('companies', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('companies') as batch:
        batch.drop_column('is_demo')
        batch.drop_column('max_users')
        batch.drop_column('trial_ends_at')
