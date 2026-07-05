"""product_relations

Revision ID: 21847344e44d
Revises: bc52912f5a4c
Create Date: 2026-07-06 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21847344e44d'
down_revision: Union[str, None] = 'bc52912f5a4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Motor 2 (§ docs/ai-engine-architecture.md) — compatibilidades/productos
    # relacionados, informativos (no disparan nada, a diferencia de catalog_rules /
    # technical_rules). Tabla nueva, aditiva pura, no hace falta batch mode ni en SQLite.
    op.create_table(
        'product_relations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column(
            'related_product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False
        ),
        sa.Column('relation_type', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_product_relations_product_id', 'product_relations', ['product_id'])
    op.create_index('ix_product_relations_related_product_id', 'product_relations', ['related_product_id'])


def downgrade() -> None:
    op.drop_table('product_relations')
