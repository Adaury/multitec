"""suppliers and material purchase info

Revision ID: a3f6c9d21b7e
Revises: e7f21a9c5d8b
Create Date: 2026-07-14 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f6c9d21b7e'
down_revision: Union[str, None] = 'e7f21a9c5d8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabla nueva, aditiva pura, no hace falta batch mode en SQLite (igual que
    # product_relations).
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('rnc', sa.String(length=30), nullable=True),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Agregar una FK a una tabla ya existente (materials) requiere batch mode en SQLite
    # (ALTER TABLE ADD CONSTRAINT no existe ahí) — mismo gotcha ya resuelto en
    # 093cf2d8eda3_audit_columns_created_by_and_updated_at.
    with op.batch_alter_table('materials', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('supplier_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('purchase_price', sa.Numeric(12, 2), nullable=True))
        batch_op.create_foreign_key('fk_materials_supplier_id_suppliers', 'suppliers', ['supplier_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('materials', recreate='always') as batch_op:
        batch_op.drop_constraint('fk_materials_supplier_id_suppliers', type_='foreignkey')
        batch_op.drop_column('purchase_price')
        batch_op.drop_column('supplier_id')

    op.drop_table('suppliers')
