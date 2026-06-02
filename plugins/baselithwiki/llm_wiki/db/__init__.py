"""Persistence layer (Postgres + pgvector).

Aggiunto in Fase 0 del rifacimento multi-tenancy. La logica vera (pool,
helpers, models) arriva in Fase 1: qui viviamo solo come pacchetto e
come singola fonte di verità per la URL di connessione (consumata da
Alembic in ``alembic/env.py`` *e* dall'app a runtime).

Pattern allineato a ``agent-jira``: psycopg3 sync + ``ConnectionPool``,
migrations Alembic scritte a mano in SQL, RLS Postgres per isolamento
tenant, ruolo applicativo ``app_runtime`` non-superuser.
"""

from llm_wiki.db.url import resolve_database_url

__all__ = ["resolve_database_url"]
