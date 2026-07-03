"""ncf sequences

Revision ID: cdbaf1a4b580
Revises: 24f27f0269fc
Create Date: 2026-07-03 04:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdbaf1a4b580'
down_revision: Union[str, None] = '24f27f0269fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ncf_sequences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ncf_type', sa.String(length=3), nullable=False),
        sa.Column('description', sa.String(length=100), nullable=False),
        sa.Column('range_start', sa.Integer(), nullable=False),
        sa.Column('range_end', sa.Integer(), nullable=False),
        sa.Column('next_number', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.Date(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False
        ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # SQLite no soporta ALTER TABLE ADD CONSTRAINT, así que necesita batch/recreate ahí.
    # En Postgres, recreate='always' reconstruye la tabla entera y eso falla porque
    # invoice_history/invoice_items tienen FKs apuntando a invoices — ahí basta el ALTER
    # nativo, mucho más barato y sin ese riesgo.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table('invoices', recreate='always') as batch_op:
            batch_op.add_column(sa.Column('ncf', sa.String(length=20), nullable=True))
            batch_op.add_column(sa.Column('ncf_type', sa.String(length=3), nullable=True))
            batch_op.create_unique_constraint('uq_invoices_ncf', ['ncf'])
    else:
        op.add_column('invoices', sa.Column('ncf', sa.String(length=20), nullable=True))
        op.add_column('invoices', sa.Column('ncf_type', sa.String(length=3), nullable=True))
        op.create_unique_constraint('uq_invoices_ncf', 'invoices', ['ncf'])


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table('invoices', recreate='always') as batch_op:
            batch_op.drop_constraint('uq_invoices_ncf', type_='unique')
            batch_op.drop_column('ncf_type')
            batch_op.drop_column('ncf')
    else:
        op.drop_constraint('uq_invoices_ncf', 'invoices', type_='unique')
        op.drop_column('invoices', 'ncf_type')
        op.drop_column('invoices', 'ncf')

    op.drop_table('ncf_sequences')
