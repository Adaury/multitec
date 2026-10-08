"""foreign key indexes

Revision ID: f5c1a7d3b9e2
Revises: e3b9c4d8a1f6
Create Date: 2026-10-08 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f5c1a7d3b9e2'
down_revision: Union[str, None] = 'e3b9c4d8a1f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PostgreSQL no indexa las claves foráneas solas: sin esto, cada "las líneas de este presupuesto"
# o "los proyectos de este cliente" recorre la tabla completa. Con pocas filas no se nota; crece
# linealmente con los datos. created_by (solo auditoría) se deja sin índice a propósito.
FOREIGN_KEY_INDEXES = [
    ('ai_feedback_events', 'product_id'),
    ('budget_items', 'budget_id'),
    ('budget_items', 'product_id'),
    ('budgets', 'project_id'),
    ('extensions', 'project_id'),
    ('extensions', 'quote_id'),
    ('invoice_history', 'invoice_id'),
    ('invoice_items', 'invoice_id'),
    ('invoices', 'project_id'),
    ('log_entries', 'project_id'),
    ('log_entry_assets', 'log_entry_id'),
    ('materials', 'product_id'),
    ('materials', 'project_id'),
    ('materials', 'supplier_id'),
    ('notifications', 'user_id'),
    ('pre_invoice_items', 'pre_invoice_id'),
    ('pre_invoices', 'project_id'),
    ('products', 'category_id'),
    ('project_stages', 'project_id'),
    ('projects', 'client_id'),
    ('projects', 'responsible_id'),
    ('quote_history', 'quote_id'),
    ('quote_items', 'product_id'),
    ('quote_items', 'quote_id'),
    ('quotes', 'project_id'),
    ('refresh_tokens', 'user_id'),
    ('stock_movements', 'product_id'),
    ('survey_assets', 'survey_id'),
    ('ticket_assets', 'ticket_id'),
    ('ticket_history', 'ticket_id'),
    ('tickets', 'project_id'),
    ('tickets', 'technician_id'),
    ('visits', 'project_id'),
    ('visits', 'technician_id'),
]


def upgrade() -> None:
    for table, column in FOREIGN_KEY_INDEXES:
        op.create_index(f'ix_{table}_{column}', table, [column], if_not_exists=True)


def downgrade() -> None:
    for table, column in reversed(FOREIGN_KEY_INDEXES):
        op.drop_index(f'ix_{table}_{column}', table_name=table, if_exists=True)
