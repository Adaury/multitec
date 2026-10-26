"""multi-empresa: tabla companies, company_id en todas las tablas de negocio y únicos por empresa

Revision ID: d9a4b7c2e1f3
Revises: c8e3f5a1d7b9
Create Date: 2026-10-26 09:00:00.000000

Todo lo que ya existía pasa a ser de la empresa 1 (la original, Multitec). El dueño (el primer administrador)
queda también como administrador de la plataforma. Se hace en una sola transacción: o se aplica todo o nada.

HAGA UN RESPALDO ANTES (deploy/backup-postgres.ps1).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd9a4b7c2e1f3'
down_revision: Union[str, None] = 'c8e3f5a1d7b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tablas que reciben company_id. audit_log lo lleva opcional (un acceso fallido no tiene empresa).
TENANT_TABLES = [
    'ai_feedback_events', 'audit_log', 'budget_items', 'budgets', 'calculation_parameters', 'catalog_rules',
    'categories', 'client_assets', 'clients', 'code_sequences', 'company_profile', 'engineering', 'extensions',
    'invoice_history', 'invoice_items', 'invoices', 'log_entries', 'log_entry_assets', 'materials', 'ncf_sequences',
    'notifications', 'pre_invoice_items', 'pre_invoices', 'product_match_corrections', 'product_relations',
    'products', 'project_embeddings', 'project_stages', 'projects', 'purchase_invoices', 'quote_history',
    'quote_items', 'quotes', 'stock_movements', 'suppliers', 'survey_assets', 'survey_markers', 'surveys',
    'technical_rules', 'ticket_assets', 'ticket_history', 'tickets', 'users', 'visits', 'voice_survey_examples',
]
NULLABLE_COMPANY = {'audit_log'}

# (tabla, columna): estos únicos globales pasan a ser únicos POR EMPRESA.
UNIQUE_INDEXES = [
    ('budgets', 'code'), ('calculation_parameters', 'key'), ('categories', 'slug'), ('extensions', 'code'),
    ('invoices', 'code'), ('pre_invoices', 'code'), ('products', 'code'), ('projects', 'code'),
    ('quotes', 'code'), ('tickets', 'code'),
]


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == 'sqlite'


def upgrade() -> None:
    bind = op.get_bind()
    sqlite = _is_sqlite()

    # 1) La tabla de empresas y la empresa 1 (nombre tomado del membrete actual si existe).
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('slug', sa.String(length=60), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_companies_slug', 'companies', ['slug'], unique=True)
    name = bind.execute(sa.text("SELECT name FROM company_profile WHERE name IS NOT NULL AND name <> '' ORDER BY id LIMIT 1")).scalar()
    bind.execute(
        sa.text("INSERT INTO companies (id, name, slug, is_active) VALUES (1, :name, 'multitec', :active)"),
        {"name": name or "Multitec", "active": True},
    )
    if not sqlite:
        bind.execute(sa.text("SELECT setval(pg_get_serial_sequence('companies', 'id'), 1)"))
        # company_profile se creaba con id=1 fijo: su secuencia quedó en 1 y el perfil de la 2.ª empresa chocaría.
        bind.execute(
            sa.text(
                "SELECT setval(pg_get_serial_sequence('company_profile', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM company_profile))"
            )
        )

    # 2) company_id en cada tabla: añadir nulo -> rellenar con la empresa 1 -> endurecer.
    for table in TENANT_TABLES:
        if sqlite:
            with op.batch_alter_table(table) as batch:
                batch.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        else:
            op.add_column(table, sa.Column('company_id', sa.Integer(), nullable=True))
        bind.execute(sa.text(f"UPDATE {table} SET company_id = 1"))
        if sqlite:
            with op.batch_alter_table(table) as batch:
                batch.alter_column('company_id', existing_type=sa.Integer(), nullable=table in NULLABLE_COMPANY)
                batch.create_foreign_key(f'fk_{table}_company_id', 'companies', ['company_id'], ['id'])
                batch.create_index(f'ix_{table}_company_id', ['company_id'])
        else:
            if table not in NULLABLE_COMPANY:
                op.alter_column(table, 'company_id', nullable=False)
            op.create_foreign_key(f'fk_{table}_company_id', table, 'companies', ['company_id'], ['id'])
            op.create_index(f'ix_{table}_company_id', table, ['company_id'])

    # 3) Administrador de la plataforma: el primer administrador (el dueño), además de su empresa.
    if sqlite:
        with op.batch_alter_table('users') as batch:
            batch.add_column(sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default=sa.false()))
    else:
        op.add_column('users', sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default=sa.false()))
    bind.execute(sa.text("UPDATE users SET is_platform_admin = :t WHERE id = (SELECT MIN(id) FROM users WHERE role = 'admin')"), {"t": True})

    # 4) Correlativos por empresa: la clave de code_sequences pasa de (prefix) a (company_id, prefix).
    if sqlite:
        with op.batch_alter_table('code_sequences', recreate='always') as batch:
            batch.create_primary_key('pk_code_sequences', ['company_id', 'prefix'])
    else:
        op.drop_constraint('code_sequences_pkey', 'code_sequences', type_='primary')
        op.create_primary_key('code_sequences_pkey', 'code_sequences', ['company_id', 'prefix'])

    # 5) Un perfil de membrete por empresa.
    if sqlite:
        with op.batch_alter_table('company_profile') as batch:
            batch.create_unique_constraint('uq_company_profile_company_id', ['company_id'])
    else:
        op.create_unique_constraint('uq_company_profile_company_id', 'company_profile', ['company_id'])

    # 6) Los códigos (PRY-, COT-, FAC-...), el slug y la clave de parámetros dejan de ser únicos globales.
    for table, column in UNIQUE_INDEXES:
        index = f'ix_{table}_{column}'
        op.drop_index(index, table_name=table)
        op.create_index(index, table, [column])  # el índice normal se queda para las búsquedas
        if sqlite:
            with op.batch_alter_table(table) as batch:
                batch.create_unique_constraint(f'uq_{table}_company_{column}', ['company_id', column])
        else:
            op.create_unique_constraint(f'uq_{table}_company_{column}', table, ['company_id', column])
    # El NCF es por empresa (cada una tiene sus propias secuencias autorizadas por la DGII).
    if sqlite:
        with op.batch_alter_table('invoices') as batch:
            batch.drop_constraint('uq_invoices_ncf', type_='unique')
            batch.create_unique_constraint('uq_invoices_company_ncf', ['company_id', 'ncf'])
    else:
        op.drop_constraint('uq_invoices_ncf', 'invoices', type_='unique')
        op.create_unique_constraint('uq_invoices_company_ncf', 'invoices', ['company_id', 'ncf'])


def downgrade() -> None:
    sqlite = _is_sqlite()
    # Volver a únicos globales solo es posible si no hay dos empresas con el mismo código: si las hay, falla a propósito.
    if sqlite:
        with op.batch_alter_table('invoices') as batch:
            batch.drop_constraint('uq_invoices_company_ncf', type_='unique')
            batch.create_unique_constraint('uq_invoices_ncf', ['ncf'])
    else:
        op.drop_constraint('uq_invoices_company_ncf', 'invoices', type_='unique')
        op.create_unique_constraint('uq_invoices_ncf', 'invoices', ['ncf'])
    for table, column in UNIQUE_INDEXES:
        index = f'ix_{table}_{column}'
        if sqlite:
            with op.batch_alter_table(table) as batch:
                batch.drop_constraint(f'uq_{table}_company_{column}', type_='unique')
        else:
            op.drop_constraint(f'uq_{table}_company_{column}', table, type_='unique')
        op.drop_index(index, table_name=table)
        op.create_index(index, table, [column], unique=True)
    if sqlite:
        with op.batch_alter_table('company_profile') as batch:
            batch.drop_constraint('uq_company_profile_company_id', type_='unique')
        with op.batch_alter_table('code_sequences', recreate='always') as batch:
            batch.create_primary_key('pk_code_sequences', ['prefix'])
    else:
        op.drop_constraint('uq_company_profile_company_id', 'company_profile', type_='unique')
        op.drop_constraint('code_sequences_pkey', 'code_sequences', type_='primary')
        op.create_primary_key('code_sequences_pkey', 'code_sequences', ['prefix'])
    if sqlite:
        with op.batch_alter_table('users') as batch:
            batch.drop_column('is_platform_admin')
    else:
        op.drop_column('users', 'is_platform_admin')
    for table in reversed(TENANT_TABLES):
        if sqlite:
            with op.batch_alter_table(table) as batch:
                batch.drop_index(f'ix_{table}_company_id')
                batch.drop_constraint(f'fk_{table}_company_id', type_='foreignkey')
                batch.drop_column('company_id')
        else:
            op.drop_index(f'ix_{table}_company_id', table_name=table)
            op.drop_constraint(f'fk_{table}_company_id', table, type_='foreignkey')
            op.drop_column(table, 'company_id')
    op.drop_index('ix_companies_slug', table_name='companies')
    op.drop_table('companies')
