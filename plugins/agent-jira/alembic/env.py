"""Alembic environment configuration.

Uses the application's DB_CONNINFO for connection so that
the same env vars drive both the app and migrations.

Plugin layout — env.py lives at ``plugins/agent-jira/alembic/env.py`` and
the configuration package lives at ``plugins/agent-jira/agent_jira/``.
Adding the plugin root to ``sys.path`` makes ``agent_jira`` importable when
alembic is invoked directly (``alembic -c plugins/agent-jira/alembic.ini upgrade head``).
"""

from logging.config import fileConfig
import os
import sys

from alembic import context

# Add the plugin root to sys.path so we can import the agent_jira package.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_jira.config import DB_CONNINFO

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the sqlalchemy.url with the app's connection string.
# Escape '%' so ConfigParser doesn't treat it as interpolation syntax
# (e.g. passwords containing URL-encoded chars like %40 for '@').
config.set_main_option("sqlalchemy.url", DB_CONNINFO.replace("%", "%%"))

target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    from sqlalchemy import create_engine

    url = config.get_main_option("sqlalchemy.url") or ""
    # Ensure SQLAlchemy uses psycopg3 driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
