"""Programmatic alembic upgrade. Used at app startup if migrations enabled."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from ..core.config import settings
from ..core.logging import log


def _build_config() -> Config:
    # Plugin-port note: upstream docheck-engine had migrate.py at
    # ``docheck-engine/src/docheck/db/migrate.py`` with alembic.ini at
    # parents[3] (== docheck-engine/). Under the plugin layout the file
    # lives at ``plugins/docheck/docheck/db/migrate.py`` with alembic.ini
    # at parents[2] (== plugins/docheck/).
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}")
    return cfg


def upgrade_to_head() -> None:
    cfg = _build_config()
    log.info("alembic.upgrade.start", db_path=str(settings.db_path))
    command.upgrade(cfg, "head")
    log.info("alembic.upgrade.done")
