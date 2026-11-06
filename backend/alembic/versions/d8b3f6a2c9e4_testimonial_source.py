"""testimonios: de dónde vienen (panel o cliente) y contacto de quien lo envió

Revision ID: d8b3f6a2c9e4
Revises: c7e2a9d4f1b6
Create Date: 2026-11-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8b3f6a2c9e4"
down_revision: Union[str, None] = "c7e2a9d4f1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("testimonials", recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(20), nullable=False, server_default="panel"))
        batch_op.add_column(sa.Column("contact", sa.String(160), nullable=True))


def downgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("testimonials", recreate=recreate) as batch_op:
        batch_op.drop_column("contact")
        batch_op.drop_column("source")
