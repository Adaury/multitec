"""ai_feedback_events budget_id

Revision ID: eccc613fdde1
Revises: 4abec1ec6eff
Create Date: 2026-07-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eccc613fdde1'
down_revision: Union[str, None] = '4abec1ec6eff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Motor 7 — scoping del análisis periódico (§ docs/ai-engine-architecture.md). Sin
    # budget_id, un evento solo se puede ubicar por project_id, y un proyecto puede tener
    # más de un Budget (recotizaciones) — eso hace ambigua la reconstrucción de "qué otros
    # productos había en el presupuesto cuando se agregó/quitó esta línea a mano", que es
    # justamente lo que necesita el análisis de patrones. Nullable y sin backfill porque
    # hoy no hay filas reales que migrar (ver el propio doc) — este es el momento barato
    # para agregar la columna, antes de que exista tráfico real.
    #
    # SQLite no soporta ALTER de constraints sin modo batch — mismo patrón ya usado en
    # d6c464c4501d y a1b2c3d4e5f6.
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table('ai_feedback_events', recreate='always') as batch_op:
            batch_op.add_column(sa.Column('budget_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_ai_feedback_events_budget_id', 'budgets', ['budget_id'], ['id'], ondelete='CASCADE'
            )
            batch_op.create_index('ix_ai_feedback_events_budget_id', ['budget_id'])
    else:
        op.add_column('ai_feedback_events', sa.Column('budget_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_ai_feedback_events_budget_id',
            'ai_feedback_events',
            'budgets',
            ['budget_id'],
            ['id'],
            ondelete='CASCADE',
        )
        op.create_index('ix_ai_feedback_events_budget_id', 'ai_feedback_events', ['budget_id'])


def downgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table('ai_feedback_events', recreate='always') as batch_op:
            batch_op.drop_index('ix_ai_feedback_events_budget_id')
            batch_op.drop_constraint('fk_ai_feedback_events_budget_id', type_='foreignkey')
            batch_op.drop_column('budget_id')
    else:
        op.drop_index('ix_ai_feedback_events_budget_id', table_name='ai_feedback_events')
        op.drop_constraint('fk_ai_feedback_events_budget_id', 'ai_feedback_events', type_='foreignkey')
        op.drop_column('ai_feedback_events', 'budget_id')
