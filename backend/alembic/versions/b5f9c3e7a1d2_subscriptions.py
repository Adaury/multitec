"""suscripciones: registro público, cobros (instalación + mensualidad) y pagos por empresa

Revision ID: b5f9c3e7a1d2
Revises: a4e8f1b6c2d9
Create Date: 2026-11-05 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5f9c3e7a1d2"
down_revision: Union[str, None] = "a4e8f1b6c2d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("companies", recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(20), nullable=False, server_default="panel"))
        batch_op.add_column(sa.Column("contact_name", sa.String(120), nullable=True))
        batch_op.add_column(sa.Column("contact_email", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("contact_phone", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("setup_fee", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("monthly_fee", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("setup_paid_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("paid_until", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "company_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.Date(), nullable=False),
        sa.Column("paid_until_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("company_payments")
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("companies", recreate=recreate) as batch_op:
        for column in ("reviewed_at", "paid_until", "setup_paid_at", "monthly_fee", "setup_fee", "contact_phone",
                       "contact_email", "contact_name", "source"):
            batch_op.drop_column(column)
