"""calculation_parameters

Revision ID: 504e4bf514d8
Revises: 99fe2962bc29
Create Date: 2026-07-05 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '504e4bf514d8'
down_revision: Union[str, None] = '99fe2962bc29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Motor 5 (§ docs/ai-engine-architecture.md) — parámetros de cálculo configurables
    # desde el ERP en vez de constantes en código. Tabla nueva, aditiva pura, no hace
    # falta batch mode ni en SQLite. Sin filas todavía: cada clave usa su default de
    # código (ver app.ai_engine.calculation.KNOWN_PARAMETERS) hasta que un admin la
    # configure.
    op.create_table(
        'calculation_parameters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(length=60), nullable=False),
        sa.Column('value', sa.Numeric(12, 4), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_calculation_parameters_key', 'calculation_parameters', ['key'], unique=True)


def downgrade() -> None:
    op.drop_table('calculation_parameters')
