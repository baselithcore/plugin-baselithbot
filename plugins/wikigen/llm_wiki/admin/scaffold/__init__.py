"""Scaffold a new Domain Pack from the ``_template`` skeleton.

Pure functional core, no I/O side-effects until ``scaffold_pack(..., dry_run=False)``
is called. ``plan_scaffold`` returns a :class:`ScaffoldPlan` (set of files
that *would* be created, ``.env`` diff preview) so the UI can show a
review step before writing.

Design notes
------------
- Path safety is enforced here, not at the API layer. Vault must resolve
  to an absolute path outside ``domains/`` and ``.git``; the slug is
  validated against ``DomainPack.name`` regex; ``_template`` is reserved.
- ``.env`` upsert preserves existing keys (API secrets are *never*
  overwritten) — only ``APP_DOMAIN`` + ``WIKI_ROOT`` are touched by default,
  plus optional provider keys when callers pass ``provider`` settings.
- ``.env`` reads + writes go through :func:`mutate_env_file`: an
  ``fcntl.flock`` on a sidecar lockfile guards against concurrent wizard
  tabs racing on the same file, and the write itself is a tempfile +
  ``os.replace`` so the on-disk bytes flip atomically.
- The CLI ``wiki-wl init`` is a thin wrapper over :func:`scaffold_pack` —
  no logic duplication.

Modular layout (>500 LOC budget):
- :mod:`.models`     — pydantic models + constants + ``ScaffoldError``
- :mod:`.paths`      — repo root / template / seed / vault resolution
- :mod:`.env_io`     — ``.env`` locking, atomic write, k/v upsert
- :mod:`.synthesis`  — LLM-backed prompt synthesis hook
- :mod:`.core`       — ``plan_scaffold`` / ``scaffold_pack`` orchestration
"""

from __future__ import annotations

# NOTE: ``_*`` symbols are re-exported for backward-compat with callers that
# imported them from the monolithic ``scaffold.py``. ``# noqa: F401`` because
# they are intentionally not in ``__all__`` (private but historically reachable).
from llm_wiki.admin.scaffold.core import (
    _replace_yaml_field,  # noqa: F401
    _upsert_env_file,  # noqa: F401
    plan_scaffold,
    scaffold_pack,
)
from llm_wiki.admin.scaffold.env_io import (
    _ENV_VALUE_FORBIDDEN,  # noqa: F401
    _atomic_write_env,  # noqa: F401
    _env_lock,  # noqa: F401
    _upsert_env_kv,  # noqa: F401
    mutate_env_file,
)
from llm_wiki.admin.scaffold.models import (
    DOMAIN_NAME_RE,
    RESERVED_NAMES,
    TEMPLATE_REQUIRED,
    FileOp,
    ProviderSettings,
    ScaffoldError,
    ScaffoldPlan,
    ScaffoldRequest,
    ScaffoldResult,
)
from llm_wiki.admin.scaffold.paths import (
    humanise as _humanise,  # noqa: F401
)
from llm_wiki.admin.scaffold.paths import (
    repo_root,
    resolve_vault_path,
    seed_pack_dir,
    template_dir,
)
from llm_wiki.admin.scaffold.synthesis import (
    _maybe_synthesise_prompts,  # noqa: F401
    _patch_pack_yaml_with_synthesis,  # noqa: F401
    _write_with_trailing_nl,  # noqa: F401
)

__all__ = [
    "DOMAIN_NAME_RE",
    "FileOp",
    "ProviderSettings",
    "RESERVED_NAMES",
    "ScaffoldError",
    "ScaffoldPlan",
    "ScaffoldRequest",
    "ScaffoldResult",
    "TEMPLATE_REQUIRED",
    "mutate_env_file",
    "plan_scaffold",
    "repo_root",
    "resolve_vault_path",
    "scaffold_pack",
    "seed_pack_dir",
    "template_dir",
]
