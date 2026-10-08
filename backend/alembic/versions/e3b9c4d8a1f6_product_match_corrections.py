"""product match corrections

Revision ID: e3b9c4d8a1f6
Revises: d2a8b5f1c7e3
Create Date: 2026-10-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b9c4d8a1f6'
down_revision: Union[str, None] = 'd2a8b5f1c7e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_match_corrections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('budget_id', sa.Integer(), sa.ForeignKey('budgets.id', ondelete='CASCADE'), nullable=True),
        sa.Column('spoken_text', sa.String(length=255), nullable=False),
        sa.Column('ai_product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('human_product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_product_match_corrections_project_id', 'product_match_corrections', ['project_id'])
    op.create_index('ix_product_match_corrections_human_product_id', 'product_match_corrections', ['human_product_id'])


def downgrade() -> None:
    op.drop_index('ix_product_match_corrections_human_product_id', table_name='product_match_corrections')
    op.drop_index('ix_product_match_corrections_project_id', table_name='product_match_corrections')
    op.drop_table('product_match_corrections')
