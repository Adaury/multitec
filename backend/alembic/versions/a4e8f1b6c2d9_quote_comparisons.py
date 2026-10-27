"""comparar cotizaciones ajenas con el levantamiento y la cotización propia

Revision ID: a4e8f1b6c2d9
Revises: f2c6d9e3a5b7
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from alembic import op

revision = 'a4e8f1b6c2d9'
down_revision = 'f2c6d9e3a5b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'quote_comparisons',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', name='fk_quote_comparisons_company_id'), nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('quote_id', sa.Integer(), sa.ForeignKey('quotes.id'), nullable=True),
        sa.Column('label', sa.String(length=120), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('total', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_quote_comparisons_company_id', 'quote_comparisons', ['company_id'])
    op.create_index('ix_quote_comparisons_project_id', 'quote_comparisons', ['project_id'])


def downgrade() -> None:
    op.drop_table('quote_comparisons')
