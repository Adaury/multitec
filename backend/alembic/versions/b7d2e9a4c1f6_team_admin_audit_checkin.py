"""equipo: ficha del técnico, sesiones, auditoría y entrada/salida de visitas

Revision ID: b7d2e9a4c1f6
Revises: a8e3f1c5d7b2
Create Date: 2026-10-25 09:00:00.000000

Todo es aditivo y con columnas opcionales: no toca datos existentes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2e9a4c1f6'
down_revision: Union[str, None] = 'a8e3f1c5d7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ficha del miembro del equipo
    op.add_column('users', sa.Column('phone', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('zone', sa.String(length=80), nullable=True))
    op.add_column('users', sa.Column('skills', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('vehicle', sa.String(length=80), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))

    # Sesiones activas
    op.add_column('refresh_tokens', sa.Column('user_agent', sa.String(length=255), nullable=True))
    op.add_column('refresh_tokens', sa.Column('ip', sa.String(length=64), nullable=True))
    op.add_column('refresh_tokens', sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True))

    # Visitas: duración estimada y entrada/salida en el sitio
    op.add_column('visits', sa.Column('duration_min', sa.Integer(), nullable=True))
    op.add_column('visits', sa.Column('checkin_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('visits', sa.Column('checkin_lat', sa.Float(), nullable=True))
    op.add_column('visits', sa.Column('checkin_lng', sa.Float(), nullable=True))
    op.add_column('visits', sa.Column('checkout_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('visits', sa.Column('checkout_lat', sa.Float(), nullable=True))
    op.add_column('visits', sa.Column('checkout_lng', sa.Float(), nullable=True))

    # Bitácora de auditoría (solo se agrega)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=60), nullable=False),
        sa.Column('entity', sa.String(length=40), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('ip', sa.String(length=64), nullable=True),
    )
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])


def downgrade() -> None:
    op.drop_index('ix_audit_log_action', table_name='audit_log')
    op.drop_index('ix_audit_log_user_id', table_name='audit_log')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_table('audit_log')
    for column in ('checkout_lng', 'checkout_lat', 'checkout_at', 'checkin_lng', 'checkin_lat', 'checkin_at', 'duration_min'):
        op.drop_column('visits', column)
    for column in ('last_used_at', 'ip', 'user_agent'):
        op.drop_column('refresh_tokens', column)
    for column in ('last_login_at', 'vehicle', 'skills', 'zone', 'phone'):
        op.drop_column('users', column)
