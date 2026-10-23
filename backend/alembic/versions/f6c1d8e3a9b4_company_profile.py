"""company_profile (membrete y logo editables)

Revision ID: f6c1d8e3a9b4
Revises: e5b9c4d7f1a3
Create Date: 2026-10-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6c1d8e3a9b4'
down_revision: Union[str, None] = 'e5b9c4d7f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'company_profile',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=True),
        sa.Column('tagline', sa.String(length=160), nullable=True),
        sa.Column('representative', sa.String(length=120), nullable=True),
        sa.Column('rnc', sa.String(length=30), nullable=True),
        sa.Column('cedula', sa.String(length=30), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=60), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('website', sa.String(length=120), nullable=True),
        sa.Column('bank_info', sa.Text(), nullable=True),
        sa.Column('invoice_notes', sa.Text(), nullable=True),
        sa.Column('logo_path', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('company_profile')
