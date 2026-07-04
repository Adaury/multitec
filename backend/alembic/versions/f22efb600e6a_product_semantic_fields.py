"""product_semantic_fields

Revision ID: f22efb600e6a
Revises: d6c464c4501d
Create Date: 2026-07-04 17:40:03.011504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f22efb600e6a'
down_revision: Union[str, None] = 'd6c464c4501d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Catálogo "inteligente": campos semánticos para que el levantamiento con IA pueda
    # mapear lenguaje libre del técnico a productos reales. Todo nullable/aditivo — sin
    # constraints nuevos, no hace falta batch mode ni siquiera en SQLite.
    op.add_column('products', sa.Column('brand', sa.String(length=80), nullable=True))
    op.add_column('products', sa.Column('model', sa.String(length=80), nullable=True))
    op.add_column('products', sa.Column('commercial_description', sa.Text(), nullable=True))
    op.add_column('products', sa.Column('technical_description', sa.Text(), nullable=True))
    op.add_column('products', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('products', sa.Column('synonyms', sa.JSON(), nullable=True))
    op.add_column('products', sa.Column('suggests_tags', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'suggests_tags')
    op.drop_column('products', 'synonyms')
    op.drop_column('products', 'tags')
    op.drop_column('products', 'technical_description')
    op.drop_column('products', 'commercial_description')
    op.drop_column('products', 'model')
    op.drop_column('products', 'brand')
