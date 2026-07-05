"""technical_rules

Revision ID: 99fe2962bc29
Revises: a1b2c3d4e5f6
Create Date: 2026-07-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99fe2962bc29'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generalización hacia adelante de catalog_rules (§ docs/ai-engine-architecture.md,
    # Motor 4) — tabla nueva en paralelo; catalog_rules no se toca ni se migra. Aditiva
    # pura (tabla nueva, sin ALTER a tablas existentes), no hace falta batch mode ni en
    # SQLite.
    op.create_table(
        'technical_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'source_product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False
        ),
        sa.Column('action_type', sa.String(length=40), nullable=False),
        sa.Column('action_params', sa.JSON(), nullable=False),
        sa.Column('notes', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_technical_rules_source_product_id', 'technical_rules', ['source_product_id'])


def downgrade() -> None:
    op.drop_table('technical_rules')
