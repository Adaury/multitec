"""quote/pre_invoice/invoice item notes

Revision ID: b3a1c7e2f4d6
Revises: 9ef7b40de9f3
Create Date: 2026-07-08 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a1c7e2f4d6'
down_revision: Union[str, None] = '9ef7b40de9f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quote_items', sa.Column('note', sa.String(length=500), nullable=True))
    op.add_column('pre_invoice_items', sa.Column('note', sa.String(length=500), nullable=True))
    op.add_column('invoice_items', sa.Column('note', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('invoice_items', 'note')
    op.drop_column('pre_invoice_items', 'note')
    op.drop_column('quote_items', 'note')
