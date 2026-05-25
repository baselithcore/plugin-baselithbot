"""Single source of truth per la connection string Postgres.

Risoluzione (precedence dall'alto):

1. ``DATABASE_URL`` env — wins se valorizzato. Forma standard
   ``postgresql://user:pass@host:port/dbname``. Se passi
   ``postgresql+psycopg://...`` viene rispettato verbatim (utile per
   forzare driver in pool SQLAlchemy).
2. Composizione da ``POSTGRES_USER``/``POSTGRES_PASSWORD``/
   ``POSTGRES_HOST``/``POSTGRES_PORT``/``POSTGRES_DB`` — comodo per
   docker-compose e per onboarding (un solo file ``.env`` con i pezzi).
3. Default dev coerenti con ``docker-compose.yml``
   (``llm_wiki/llm_wiki_dev@localhost:5432/llm_wiki``).

Usato sia da :mod:`llm_wiki.db.connection` (pool runtime) sia da
``alembic/env.py`` (migrations) — single source of truth, nessuna
divergenza fra "URL che usa l'app" e "URL che usano le migrations".
"""

from __future__ import annotations

import os
from urllib.parse import quote


def resolve_database_url() -> str:
    """Restituisce la URL Postgres effettiva. Mai vuota, mai None."""
    explicit = (os.getenv("DATABASE_URL") or "").strip()
    if explicit:
        if "@postgres:" in explicit or "@postgres/" in explicit:
            import socket

            try:
                socket.gethostbyname("postgres")
            except socket.gaierror:
                if "@postgres:" in explicit:
                    explicit = explicit.replace("@postgres:", "@127.0.0.1:", 1)
                elif "@postgres/" in explicit:
                    explicit = explicit.replace("@postgres/", "@127.0.0.1/", 1)
        return explicit

    user = (os.getenv("POSTGRES_USER") or "llm_wiki").strip()
    password = (os.getenv("POSTGRES_PASSWORD") or "llm_wiki_dev").strip()
    host = (os.getenv("POSTGRES_HOST") or "localhost").strip()

    if host == "postgres":
        import socket

        try:
            socket.gethostbyname("postgres")
        except socket.gaierror:
            host = "127.0.0.1"

    # Porta host default 5433 — allineata a docker-compose.yml che mappa
    # 5433 host → 5432 container per evitare clash con altri progetti
    # Postgres locali (agent-jira, baselith, ecc.). Override via env per
    # deploy diversi.
    port = (os.getenv("POSTGRES_PORT") or "5433").strip()
    db = (os.getenv("POSTGRES_DB") or "llm_wiki").strip()
    # quote() su user/pass evita rotture quando contengono `@` `:` `/`.
    return f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{db}"


__all__ = ["resolve_database_url"]
