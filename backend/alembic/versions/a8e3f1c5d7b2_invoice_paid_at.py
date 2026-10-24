"""invoice paid_at (fecha de cobro, para el seguimiento de cobros)

Revision ID: a8e3f1c5d7b2
Revises: f6c1d8e3a9b4
Create Date: 2026-10-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8e3f1c5d7b2'
down_revision: Union[str, None] = 'f6c1d8e3a9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('invoices', sa.Column('paid_at', sa.Date(), nullable=True))
    # Las facturas que ya tienen una forma de pago al contado (efectivo, transferencia, tarjeta…) se
    # dan por cobradas el día que se emitieron; las de crédito o sin forma de pago quedan por cobrar.
    op.execute(
        "UPDATE invoices SET paid_at = CAST(created_at AS DATE) "
        "WHERE payment_method IS NOT NULL AND payment_method <> 'credito' AND voided_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column('invoices', 'paid_at')
