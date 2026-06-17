"""BaselithBrain runtime configuration.

Pydantic-settings reader scoped to the plugin. All knobs resolve from the
process environment (after :mod:`_bootstrap` has promoted ``BASELITHBRAIN_*``
overrides to bare keys). Defaults are local-first and infra-free: a working
vault, in-memory derived index, semantic search opt-in only.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Plugin root (``plugins/baselithbrain``). The vault lives *inside* the plugin
#: by default and a relative override is resolved against it — never against the
#: process CWD — so running the host from the repo root can't scatter a stray
#: ``vault/`` there.
_PLUGIN_DIR = Path(__file__).resolve().parent


class BrainSettings(BaseSettings):
    """Operator-tunable settings for the second-brain backend."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    #: Absolute path to the Markdown vault (source of truth). Defaults to
    #: ``<plugin>/vault``; a relative override is anchored to the plugin dir.
    vault_root: Path = Field(default=_PLUGIN_DIR / "vault")

    @field_validator("vault_root")
    @classmethod
    def _anchor_vault(cls, v: Path) -> Path:
        return v if v.is_absolute() else (_PLUGIN_DIR / v).resolve()

    #: Enable derived semantic edges + semantic search. Requires an embedder
    #: (sentence-transformers). Off by default → zero external dependencies.
    semantic_enabled: bool = Field(default=False)

    #: Re-scan the vault on file changes (needs ``watchfiles``). Off by default;
    #: the API exposes an explicit ``/reindex`` for manual refresh.
    watch_enabled: bool = Field(default=False)

    #: Score each chat answer for groundedness (faithfulness to the cited
    #: notes) using the host's LLM-as-judge. Runs *after* the answer streams, so
    #: it never delays visible tokens — only adds a trailing trust badge. Costs
    #: one extra LLM call per turn; on by default, set false to disable.
    groundedness_enabled: bool = Field(default=True)

    #: Hard cap on ReAct iterations for deep-research mode (LoopBudget-style
    #: guard on cost/latency — each iteration is one LLM call). 1–12.
    research_max_iterations: int = Field(default=6, ge=1, le=12)

    #: Similarity threshold for derived (semantic) edges in the graph.
    semantic_edge_threshold: float = Field(default=0.55, ge=0.0, le=1.0)

    #: Cap on derived edges per note to keep the graph readable.
    semantic_edges_per_note: int = Field(default=5, ge=0, le=50)


@lru_cache(maxsize=1)
def get_settings() -> BrainSettings:
    """Return the process-wide settings singleton."""
    return BrainSettings()
