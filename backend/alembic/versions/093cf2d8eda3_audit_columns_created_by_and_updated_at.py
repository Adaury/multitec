"""audit columns created_by and updated_at

Revision ID: 093cf2d8eda3
Revises: 142ba692737d
Create Date: 2026-07-02 22:37:25.535779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '093cf2d8eda3'
down_revision: Union[str, None] = '142ba692737d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SQLite no soporta ALTER TABLE ADD CONSTRAINT — op.batch_alter_table usa la estrategia
# de copiar-y-recrear tabla ahí (no-op equivalente a ALTER normal en Postgres).
# recreate='always' evita un CircularDependencyError que SQLAlchemy dispara al intentar
# reordenar columnas automáticamente cuando se agregan varias a la vez.
TABLES_WITH_TIMESTAMPS = ("clients", "engineering", "products", "surveys")
TABLES_WITHOUT_TIMESTAMPS = ("budgets", "extensions", "invoices", "materials", "pre_invoices", "projects", "quotes", "tickets")


def upgrade() -> None:
    for table in TABLES_WITH_TIMESTAMPS:
        with op.batch_alter_table(table, recreate='always') as batch_op:
            batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
            batch_op.add_column(
                sa.Column(
                    'created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False
                )
            )
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
            batch_op.create_foreign_key(f"fk_{table}_created_by_users", 'users', ['created_by'], ['id'])

    for table in TABLES_WITHOUT_TIMESTAMPS:
        with op.batch_alter_table(table, recreate='always') as batch_op:
            batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
            if table != 'invoices':
                batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
            batch_op.create_foreign_key(f"fk_{table}_created_by_users", 'users', ['created_by'], ['id'])

    with op.batch_alter_table('log_entries', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('log_entries', recreate='always') as batch_op:
        batch_op.drop_column('updated_at')

    for table in reversed(TABLES_WITHOUT_TIMESTAMPS):
        with op.batch_alter_table(table, recreate='always') as batch_op:
            batch_op.drop_constraint(f"fk_{table}_created_by_users", type_='foreignkey')
            if table != 'invoices':
                batch_op.drop_column('updated_at')
            batch_op.drop_column('created_by')

    for table in reversed(TABLES_WITH_TIMESTAMPS):
        with op.batch_alter_table(table, recreate='always') as batch_op:
            batch_op.drop_constraint(f"fk_{table}_created_by_users", type_='foreignkey')
            batch_op.drop_column('updated_at')
            batch_op.drop_column('created_at')
            batch_op.drop_column('created_by')
