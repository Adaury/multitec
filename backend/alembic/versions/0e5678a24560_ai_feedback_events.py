"""ai_feedback_events

Revision ID: 0e5678a24560
Revises: 504e4bf514d8
Create Date: 2026-07-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e5678a24560'
down_revision: Union[str, None] = '504e4bf514d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Motor 7 (§ docs/ai-engine-architecture.md) — captura pasiva de correcciones humanas
    # sobre lo que la IA generó. `ai_generated` es aditivo con default (no hace falta
    # batch mode ni en SQLite, mismo patrón que products.stock_quantity en
    # f505c83c6a23_inventory_stock_movements.py); `ai_feedback_events` es tabla nueva.
    op.add_column('budgets', sa.Column('ai_generated', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('engineering', sa.Column('ai_generated', sa.Boolean(), server_default='false', nullable=False))

    op.create_table(
        'ai_feedback_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False
        ),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('origin', sa.String(length=20), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('field_changed', sa.String(length=40), nullable=True),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_ai_feedback_events_project_id', 'ai_feedback_events', ['project_id'])


def downgrade() -> None:
    op.drop_table('ai_feedback_events')
    op.drop_column('engineering', 'ai_generated')
    op.drop_column('budgets', 'ai_generated')
