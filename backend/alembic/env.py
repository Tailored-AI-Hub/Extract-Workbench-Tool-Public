import sys
import os
from src.db import Base
from logging.config import fileConfig
from sqlalchemy import engine_from_config, inspect as sqlalchemy_inspect
from sqlalchemy import pool
from alembic import context
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def get_url():
    """Get database URL from environment variables"""
    from src.constants import DATABASE_URL
    return DATABASE_URL


def check_schema_compliance(connection, target_metadata):
    """
    Check if the current database schema matches the target metadata.
    Returns a tuple (is_compliant, missing_tables, extra_tables, differences).
    """
    inspector = sqlalchemy_inspect(connection)
    existing_tables = set(inspector.get_table_names())
    required_tables = set(target_metadata.tables.keys())
    
    missing_tables = required_tables - existing_tables
    extra_tables = existing_tables - required_tables
    
    # Check for differences in existing tables
    differences = []
    for table_name in existing_tables & required_tables:
        table = target_metadata.tables[table_name]
        db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
        model_columns = {col.name: col for col in table.columns}
        
        # Check for missing columns
        missing_cols = set(model_columns.keys()) - set(db_columns.keys())
        if missing_cols:
            differences.append({
                'table': table_name,
                'type': 'missing_columns',
                'columns': list(missing_cols)
            })
        
        # Check for extra columns (non-critical, just log)
        extra_cols = set(db_columns.keys()) - set(model_columns.keys())
        if extra_cols:
            differences.append({
                'table': table_name,
                'type': 'extra_columns',
                'columns': list(extra_cols)
            })
    
    is_compliant = len(missing_tables) == 0 and all(
        diff['type'] != 'missing_columns' for diff in differences
    )
    
    return is_compliant, missing_tables, extra_tables, differences


def get_migration_status(connection, script_dir):
    """
    Get the current migration status.
    Returns (current_revision, target_revision, has_pending_migrations).
    """
    context = MigrationContext.configure(connection)
    current_revision = context.get_current_revision()
    
    # Get the head revision (target)
    head_revision = script_dir.get_current_head()
    
    # Check if there are pending migrations
    if current_revision is None:
        # No migrations have been run
        has_pending = head_revision is not None
    else:
        # Check if current is behind head
        has_pending = current_revision != head_revision
    
    return current_revision, head_revision, has_pending


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

