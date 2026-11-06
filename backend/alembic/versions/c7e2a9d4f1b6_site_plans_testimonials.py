"""página pública: planes (precios en US$), testimonios y plan de cada empresa

Revision ID: c7e2a9d4f1b6
Revises: b5f9c3e7a1d2
Create Date: 2026-11-06 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e2a9d4f1b6"
down_revision: Union[str, None] = "b5f9c3e7a1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("monthly_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("setup_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("highlighted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_table(
        "testimonials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("role", sa.String(120), nullable=True),
        sa.Column("company", sa.String(120), nullable=True),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_example", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("companies", recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column("plan_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_companies_plan_id_platform_plans", "platform_plans", ["plan_id"], ["id"])


def downgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("companies", recreate=recreate) as batch_op:
        batch_op.drop_constraint("fk_companies_plan_id_platform_plans", type_="foreignkey")
        batch_op.drop_column("plan_id")
    op.drop_table("testimonials")
    op.drop_table("platform_plans")
