"""purchase invoices (606)

Revision ID: b7e4d1c9a2f3
Revises: f5c1a7d3b9e2
Create Date: 2026-10-08 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4d1c9a2f3'
down_revision: Union[str, None] = 'f5c1a7d3b9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabla nueva, aditiva pura: no hace falta batch mode en SQLite.
    op.create_table(
        'purchase_invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('ncf', sa.String(length=19), nullable=False),
        sa.Column('ncf_modified', sa.String(length=19), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('expense_type', sa.String(length=2), nullable=False),
        sa.Column('payment_type', sa.String(length=2), nullable=False),
        sa.Column('services_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('goods_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('itbis_invoiced', sa.Numeric(12, 2), nullable=False),
        sa.Column('itbis_withheld', sa.Numeric(12, 2), nullable=False),
        sa.Column('isr_withheld', sa.Numeric(12, 2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_purchase_invoices_supplier_id', 'purchase_invoices', ['supplier_id'])
    op.create_index('ix_purchase_invoices_project_id', 'purchase_invoices', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_purchase_invoices_project_id', table_name='purchase_invoices')
    op.drop_index('ix_purchase_invoices_supplier_id', table_name='purchase_invoices')
    op.drop_table('purchase_invoices')
