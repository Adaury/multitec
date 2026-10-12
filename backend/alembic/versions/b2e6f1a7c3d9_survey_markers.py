"""survey markers (puntos numerados sobre las fotos del levantamiento)

Revision ID: b2e6f1a7c3d9
Revises: a1d5c8e2f9b7
Create Date: 2026-10-11 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2e6f1a7c3d9'
down_revision: Union[str, None] = 'a1d5c8e2f9b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'survey_markers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('survey_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=80), nullable=True),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_survey_markers_asset_id', 'survey_markers', ['asset_id'])


def downgrade() -> None:
    op.drop_index('ix_survey_markers_asset_id', table_name='survey_markers')
    op.drop_table('survey_markers')
