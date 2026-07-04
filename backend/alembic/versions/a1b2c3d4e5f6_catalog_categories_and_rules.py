"""catalog_categories_and_rules

Revision ID: a1b2c3d4e5f6
Revises: f22efb600e6a
Create Date: 2026-07-05 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.taxonomy import LEGACY_SLUG_MAP, TAXONOMY

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f22efb600e6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insert_taxonomy(conn, categories_table) -> dict[str, int]:
    """Inserta el árbol de app/db/taxonomy.py y devuelve un mapa slug -> id."""
    slug_to_id: dict[str, int] = {}

    def insert_node(node: dict, parent_id: int | None) -> None:
        result = conn.execute(
            categories_table.insert().values(
                name=node["name"],
                slug=node["slug"],
                code_prefix=node.get("code_prefix"),
                parent_id=parent_id,
            )
        )
        node_id = result.inserted_primary_key[0]
        slug_to_id[node["slug"]] = node_id
        for child in node.get("children", []):
            insert_node(child, node_id)

    for root in TAXONOMY:
        insert_node(root, None)

    return slug_to_id


def _legacy_slug_for(old_category: str | None, name: str) -> str:
    """Heurística de backfill: 'camara'/'cableado'/'switch' no alcanzan solos para elegir
    subcategoría — se revisa el nombre del producto antes de caer al default del mapa."""
    lowered = (name or "").lower()

    if old_category == "camara":
        if "bullet" in lowered:
            return "camaras-bullet"
        if "domo" in lowered:
            return "camaras-domo"
        if "ptz" in lowered:
            return "camaras-ptz"
        if "termica" in lowered or "térmica" in lowered:
            return "camaras-termicas"
        if "analog" in lowered:
            return "camaras-analogicas"
        return "camaras-ip"

    if old_category == "cableado":
        if "fibra" in lowered and "mono" in lowered:
            return "cable-fibra-optica-monomodo"
        if "fibra" in lowered:
            return "cable-fibra-optica-multimodo"
        return "otros-cableado"

    if old_category == "switch":
        if "administrable" in lowered:
            return "switch-administrable"
        return "switch-poe"

    return LEGACY_SLUG_MAP.get(old_category or "otro", "otros")


def upgrade() -> None:
    conn = op.get_bind()

    categories_table = op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('code_prefix', sa.String(length=10), nullable=True),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_categories_slug', 'categories', ['slug'], unique=True)

    op.create_table(
        'catalog_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'source_product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False
        ),
        sa.Column('target_tag', sa.String(length=60), nullable=False),
        sa.Column('per_source_units', sa.Numeric(12, 2), nullable=True),
        sa.Column('quantity', sa.Numeric(12, 2), nullable=False, server_default='1'),
        sa.Column('notes', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_catalog_rules_source_product_id', 'catalog_rules', ['source_product_id'])

    slug_to_id = _insert_taxonomy(conn, categories_table)

    op.add_column('products', sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id'), nullable=True))

    products_table = sa.table(
        'products',
        sa.column('id', sa.Integer),
        sa.column('category', sa.String),
        sa.column('name', sa.String),
        sa.column('category_id', sa.Integer),
        sa.column('suggests_tags', sa.JSON),
    )
    catalog_rules_table = sa.table(
        'catalog_rules',
        sa.column('source_product_id', sa.Integer),
        sa.column('target_tag', sa.String),
        sa.column('per_source_units', sa.Numeric),
        sa.column('quantity', sa.Numeric),
        sa.column('notes', sa.String),
    )

    rows = conn.execute(sa.select(products_table.c.id, products_table.c.category, products_table.c.name)).fetchall()
    for product_id, old_category, name in rows:
        slug = _legacy_slug_for(old_category, name)
        category_id = slug_to_id.get(slug, slug_to_id["otros"])
        conn.execute(
            products_table.update().where(products_table.c.id == product_id).values(category_id=category_id)
        )

    # suggests_tags (JSON) -> filas catalog_rules en modo fijo, para no perder el
    # comportamiento vigente antes de eliminar la columna.
    tag_rows = conn.execute(sa.select(products_table.c.id, products_table.c.suggests_tags)).fetchall()
    for product_id, suggests_tags in tag_rows:
        for tag in suggests_tags or []:
            conn.execute(
                catalog_rules_table.insert().values(
                    source_product_id=product_id,
                    target_tag=tag,
                    per_source_units=None,
                    quantity=1,
                    notes="Migrado desde suggests_tags",
                )
            )

    op.drop_column('products', 'category')
    op.drop_column('products', 'suggests_tags')


def downgrade() -> None:
    op.add_column('products', sa.Column('suggests_tags', sa.JSON(), nullable=True))
    op.add_column('products', sa.Column('category', sa.String(length=30), nullable=True))

    conn = op.get_bind()
    products_table = sa.table(
        'products',
        sa.column('id', sa.Integer),
        sa.column('category', sa.String),
        sa.column('category_id', sa.Integer),
    )
    categories_table = sa.table(
        'categories', sa.column('id', sa.Integer), sa.column('slug', sa.String), sa.column('parent_id', sa.Integer)
    )
    slug_by_id = {row[0]: row[1] for row in conn.execute(sa.select(categories_table.c.id, categories_table.c.slug))}
    inverse_map = {v: k for k, v in LEGACY_SLUG_MAP.items()}
    for product_id, category_id in conn.execute(sa.select(products_table.c.id, products_table.c.category_id)):
        slug = slug_by_id.get(category_id)
        old_category = inverse_map.get(slug, "otro")
        conn.execute(
            products_table.update().where(products_table.c.id == product_id).values(category=old_category)
        )

    op.alter_column('products', 'category', nullable=False)
    op.drop_column('products', 'category_id')
    op.drop_table('catalog_rules')
    op.drop_table('categories')
