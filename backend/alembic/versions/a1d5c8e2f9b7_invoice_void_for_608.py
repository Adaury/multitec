"""invoice void (formato 608)

Revision ID: a1d5c8e2f9b7
Revises: f7a3c1e9b2d4
Create Date: 2026-10-11 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1d5c8e2f9b7'
down_revision: Union[str, None] = 'f7a3c1e9b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Todo nullable: las facturas existentes siguen siendo ventas vigentes.
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.add_column(sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('void_reason', sa.String(length=2), nullable=True))
        batch_op.add_column(sa.Column('voided_by', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_invoices_voided_by_users', 'users', ['voided_by'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.drop_constraint('fk_invoices_voided_by_users', type_='foreignkey')
        batch_op.drop_column('voided_by')
        batch_op.drop_column('void_reason')
        batch_op.drop_column('voided_at')
