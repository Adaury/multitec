"""equipos instalados por cliente (serial, MAC, ubicación, garantía)

Revision ID: c8e3f5a1d7b9
Revises: b7d2e9a4c1f6
Create Date: 2026-10-25 12:00:00.000000

Tabla nueva; no toca datos existentes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e3f5a1d7b9'
down_revision: Union[str, None] = 'b7d2e9a4c1f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'client_assets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('kind', sa.String(length=40), nullable=False, server_default='otro'),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('brand', sa.String(length=60), nullable=True),
        sa.Column('model', sa.String(length=60), nullable=True),
        sa.Column('serial', sa.String(length=80), nullable=True),
        sa.Column('mac', sa.String(length=17), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('location', sa.String(length=160), nullable=True),
        sa.Column('installed_on', sa.Date(), nullable=True),
        sa.Column('warranty_until', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_client_assets_client_id', 'client_assets', ['client_id'])
    op.create_index('ix_client_assets_project_id', 'client_assets', ['project_id'])
    op.create_index('ix_client_assets_serial', 'client_assets', ['serial'])
    op.create_index('ix_client_assets_mac', 'client_assets', ['mac'])
    op.create_index('ix_client_assets_warranty_until', 'client_assets', ['warranty_until'])


def downgrade() -> None:
    for name in ('warranty_until', 'mac', 'serial', 'project_id', 'client_id'):
        op.drop_index(f'ix_client_assets_{name}', table_name='client_assets')
    op.drop_table('client_assets')
