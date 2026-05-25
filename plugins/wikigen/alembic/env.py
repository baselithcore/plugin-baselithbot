"""Alembic environment.

Risolve la connessione runtime leggendo ``DATABASE_URL`` direttamente
dall'env (o componendo da ``POSTGRES_*``). Stesso codice usato dal pool
applicativo in ``llm_wiki/db/connection.py`` — single source of truth.

Pattern allineato a agent-jira: zero ``target_metadata`` (migrations
scritte a mano in SQL), psycopg3 forzato come driver SQLAlchemy.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

# Permette `from llm_wiki.db.url import resolve_database_url` quando
# Alembic invoca env.py fuori dal contesto Python normale.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Lazy import: l'helper esiste solo dopo Fase 1. Fallback a env-only.
try:
    from llm_wiki.db.url import resolve_database_url  # type: ignore
except Exception:  # pragma: no cover — Fase 0

    def resolve_database_url() -> str:
        url = os.getenv("DATABASE_URL", "").strip()
        if url:
            if "@postgres:" in url or "@postgres/" in url:
                import socket

                try:
                    socket.gethostbyname("postgres")
                except socket.gaierror:
                    if "@postgres:" in url:
                        url = url.replace("@postgres:", "@127.0.0.1:", 1)
                    elif "@postgres/" in url:
                        url = url.replace("@postgres/", "@127.0.0.1/", 1)
            return url
        user = os.getenv("POSTGRES_USER", "llm_wiki")
        password = os.getenv("POSTGRES_PASSWORD", "llm_wiki_dev")
        host = os.getenv("POSTGRES_HOST", "localhost")
        if host == "postgres":
            import socket

            try:
                socket.gethostbyname("postgres")
            except socket.gaierror:
                host = "127.0.0.1"
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "llm_wiki")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Escape `%` per ConfigParser (password URL-encoded).
_url = resolve_database_url()
config.set_main_option("sqlalchemy.url", _url.replace("%", "%%"))

# Migrations sono scritte a mano (op.execute con SQL); nessun
# autogenerate basato su modelli ORM.
target_metadata = None


def run_migrations_offline() -> None:
    """Emit raw SQL su stdout (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Esegue migrations contro DB live."""
    from sqlalchemy import create_engine

    url = config.get_main_option("sqlalchemy.url") or ""
    # Forza psycopg3 driver (default SA è psycopg2 binario).
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    connectable = create_engine(url, future=True)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
