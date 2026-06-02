"""Repo/vault path resolution helpers for scaffolding."""

from __future__ import annotations

from pathlib import Path

from llm_wiki.admin.scaffold.models import DOMAIN_NAME_RE, ScaffoldError


def repo_root() -> Path:
    """Project root: the directory holding both ``pyproject.toml`` and ``domains/``."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "domains").exists():
            return parent
    return here.parents[2]


def template_dir() -> Path:
    return repo_root() / "domains" / "_template"


def seed_pack_dir(slug: str) -> Path:
    """Resolve a seed pack directory by slug. Validates existence + seed flag.

    Used by ``scaffold_pack`` when ``from_seed`` is set: the new pack is
    forked from the seed's full layout (prompts, schema, examples)
    instead of the bare ``_template``.
    """
    import yaml  # local import to keep CLI import surface tight

    if not DOMAIN_NAME_RE.match(slug) or slug.startswith("_"):
        raise ScaffoldError(f"invalid seed slug: {slug!r}")
    candidate = repo_root() / "domains" / slug
    pack_yaml = candidate / "pack.yaml"
    if not pack_yaml.is_file():
        raise ScaffoldError(f"seed pack not found: {slug}")
    try:
        data = yaml.safe_load(pack_yaml.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ScaffoldError(f"seed pack {slug} has invalid YAML: {exc}") from exc
    if not data.get("seed"):
        raise ScaffoldError(
            f"pack {slug!r} is not marked as seed; cannot fork from a user pack"
        )
    return candidate


def resolve_vault_path(name: str, raw: str) -> Path:
    """Resolve and validate the requested vault directory.

    Rules:
    - empty input → ``<repo>/vaults/<name>``
    - explicit input must be absolute (after ``~`` expansion)
    - cannot be the repo root, ``domains/``, ``.git/``, ``_template`` dir
    - cannot be a symlink already pointing inside ``domains/``
    """
    rr = repo_root()
    if not raw:
        return (rr / "vaults" / name).resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise ScaffoldError("vault_root must be absolute")
    candidate = candidate.resolve()

    forbidden = {
        rr.resolve(),
        (rr / ".git").resolve(),
        (rr / "domains").resolve(),
        (rr / "llm_wiki").resolve(),
        (rr / "frontend").resolve(),
    }
    if candidate in forbidden:
        raise ScaffoldError(
            f"vault_root cannot be `{candidate}` (reserved engine path)"
        )
    domains_root = (rr / "domains").resolve()
    try:
        candidate.relative_to(domains_root)
    except ValueError:
        pass
    else:
        raise ScaffoldError("vault_root cannot live inside `domains/`")
    return candidate


def humanise(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").title()
