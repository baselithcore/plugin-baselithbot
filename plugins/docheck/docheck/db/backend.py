"""DB DSN selection: SQLite (MVP) or Postgres (multi-tenant)."""

from ..core.config import settings


def build_dsn() -> str:
    if settings.db_backend == "postgres":
        if not settings.postgres_dsn:
            raise RuntimeError("DOCHECK_POSTGRES_DSN required when db_backend=postgres")
        return settings.postgres_dsn
    return f"sqlite+aiosqlite:///{settings.db_path}"


def is_multitenant() -> bool:
    return settings.multitenant_enabled and settings.db_backend == "postgres"
