"""página pública: empresas aliadas

Revision ID: e4a7c1d9b3f5
Revises: d8b3f6a2c9e4
Create Date: 2026-11-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4a7c1d9b3f5"
down_revision: Union[str, None] = "d8b3f6a2c9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "site_partners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("url", sa.String(300), nullable=True),
        sa.Column("logo_url", sa.String(300), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("site_partners")
