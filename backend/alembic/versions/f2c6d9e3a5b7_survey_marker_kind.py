"""puntos marcados: tipo de equipo (cámara, NVR, switch...)

Revision ID: f2c6d9e3a5b7
Revises: e1b5c8d2f4a6
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from alembic import op

revision = 'f2c6d9e3a5b7'
down_revision = 'e1b5c8d2f4a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('survey_markers', sa.Column('kind', sa.String(length=30), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('survey_markers') as batch:
        batch.drop_column('kind')
