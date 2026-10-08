"""voice survey examples

Revision ID: d2a8b5f1c7e3
Revises: c91d4e7a2f58
Create Date: 2026-10-08 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2a8b5f1c7e3'
down_revision: Union[str, None] = 'c91d4e7a2f58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'voice_survey_examples',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('ai_notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('ai_measurements', sa.Text(), nullable=False, server_default=''),
        sa.Column('ai_observations', sa.Text(), nullable=False, server_default=''),
        sa.Column('final_notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('final_measurements', sa.Text(), nullable=False, server_default=''),
        sa.Column('final_observations', sa.Text(), nullable=False, server_default=''),
        sa.Column('ai_classified', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('corrected', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_voice_survey_examples_project_id', 'voice_survey_examples', ['project_id'])
    op.create_index('ix_voice_survey_examples_corrected', 'voice_survey_examples', ['corrected'])


def downgrade() -> None:
    op.drop_index('ix_voice_survey_examples_corrected', table_name='voice_survey_examples')
    op.drop_index('ix_voice_survey_examples_project_id', table_name='voice_survey_examples')
    op.drop_table('voice_survey_examples')
