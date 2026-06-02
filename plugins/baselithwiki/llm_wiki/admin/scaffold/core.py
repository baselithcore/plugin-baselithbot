"""Plan + apply orchestration for scaffold operations."""

from __future__ import annotations

import logging
import os as _os
import re
import shutil
from pathlib import Path
from typing import Any

from llm_wiki.admin.scaffold.env_io import (
    _upsert_env_kv,
    mutate_env_file,
)
from llm_wiki.admin.scaffold.models import (
    TEMPLATE_REQUIRED,
    ScaffoldError,
    ScaffoldPlan,
    ScaffoldRequest,
    ScaffoldResult,
)
from llm_wiki.admin.scaffold.paths import (
    humanise,
    repo_root,
    resolve_vault_path,
    seed_pack_dir,
    template_dir,
)
from llm_wiki.admin.scaffold.synthesis import _maybe_synthesise_prompts
from llm_wiki.admin.vault_seed import read_pack_data, seed_vault

logger = logging.getLogger(__name__)


def plan_scaffold(req: ScaffoldRequest) -> ScaffoldPlan:
    """Compute the file/env operations a scaffold would perform.

    Side-effect free (no writes). Validates that the template/seed
    source exists; does NOT validate writability of ``vault_path`` —
    that surfaces at apply time as ``OSError`` and is reported back to
    the caller.
    """
    if req.from_seed:
        source = seed_pack_dir(req.from_seed)
        source_label = f"seed:{req.from_seed}"
    else:
        source = template_dir()
        source_label = "_template"
    if not source.is_dir():
        raise ScaffoldError(f"scaffold source not found at {source}")
    for required in TEMPLATE_REQUIRED:
        if not (source / required).exists():
            raise ScaffoldError(f"{source_label} incomplete: missing {required}")

    if req.from_seed and req.name == req.from_seed:
        raise ScaffoldError("forked pack name must differ from the seed slug")

    label = req.label.strip() or humanise(req.name)
    description = (
        req.description.strip() or f"White-label LLM wiki for the {req.name} domain."
    )
    target = repo_root() / "domains" / req.name
    vault_path = resolve_vault_path(req.name, req.vault_root)

    pack_exists = target.exists()
    operations: list[dict[str, str]] = []
    if pack_exists and req.force:
        operations.append(
            {"kind": "remove", "target": str(target), "note": "force overwrite"}
        )
    operations.append(
        {"kind": "copy", "target": str(target), "note": f"from {source_label}"}
    )
    operations.append(
        {"kind": "edit", "target": str(target / "pack.yaml"), "note": "customise"}
    )
    for sub in ("wiki", "raw"):
        operations.append(
            {"kind": "mkdir", "target": str(vault_path / sub), "note": ""}
        )

    # Vault seed files mandated by istruzioni.md (Karpathy pattern).
    pack_data = read_pack_data(source)
    page_types: list[dict[str, Any]] = pack_data.get("page_types") or []
    for pt in page_types:
        folder = pt.get("folder") or pt.get("plural") or pt.get("id")
        if folder:
            operations.append(
                {
                    "kind": "mkdir",
                    "target": str(vault_path / "wiki" / str(folder)),
                    "note": f"page_type={pt.get('id')}",
                }
            )
    operations.append(
        {
            "kind": "write",
            "target": str(vault_path / "wiki" / "index.md"),
            "note": "catalog",
        }
    )
    operations.append(
        {
            "kind": "write",
            "target": str(vault_path / "wiki" / "log.md"),
            "note": "chronological",
        }
    )
    operations.append(
        {
            "kind": "write",
            "target": str(vault_path / "CLAUDE.md"),
            "note": "agent schema",
        }
    )

    env_diff: list[dict[str, str]] = []
    if req.write_env:
        if req.activate:
            env_diff.append({"key": "APP_DOMAIN", "value": req.name})
        env_diff.append({"key": "WIKI_ROOT", "value": str(vault_path)})
        prov = req.provider
        if prov is not None:
            if prov.vendor:
                env_diff.append({"key": "LLM_VENDOR", "value": prov.vendor})
            if prov.model and prov.vendor == "ollama":
                env_diff.append({"key": "OLLAMA_MODEL", "value": prov.model})
            if prov.model and prov.vendor == "openai":
                env_diff.append({"key": "OPENAI_MODEL", "value": prov.model})
            if prov.base_url and prov.vendor == "ollama":
                env_diff.append({"key": "OLLAMA_URL", "value": prov.base_url})
            if prov.base_url and prov.vendor == "openai":
                env_diff.append({"key": "OPENAI_API_BASE", "value": prov.base_url})
            if prov.api_key and prov.vendor == "openai":
                env_diff.append(
                    {"key": "OPENAI_API_KEY", "value": "***"}
                )  # never echo secret

    return ScaffoldPlan(
        name=req.name,
        label=label,
        description=description,
        language=req.language,
        target_pack_dir=target,
        vault_path=vault_path,
        will_overwrite=pack_exists and req.force,
        pack_dir_exists=pack_exists,
        operations=operations,
        env_diff=env_diff,
        next_steps=_next_steps(req.name, req.activate and req.write_env),
    )


def scaffold_pack(req: ScaffoldRequest) -> ScaffoldResult:
    """Apply the scaffold operation. Idempotent unless ``force=True``."""
    plan = plan_scaffold(req)

    if plan.pack_dir_exists and not req.force:
        raise ScaffoldError(
            f"domain `{req.name}` already exists at {plan.target_pack_dir}. "
            f"Pass force=true to overwrite."
        )

    target = plan.target_pack_dir
    if plan.will_overwrite and target.exists():
        shutil.rmtree(target)

    source = seed_pack_dir(req.from_seed) if req.from_seed else template_dir()
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))

    pack_yaml = target / "pack.yaml"
    text = pack_yaml.read_text(encoding="utf-8")
    text = _replace_yaml_field(text, "name", req.name)
    text = _replace_yaml_field(text, "label", plan.label, quoted=True)
    text = _replace_yaml_field(text, "description", plan.description, quoted=True)
    text = _replace_yaml_field(text, "language", req.language)
    text = _replace_yaml_field(text, "app_name", plan.label, quoted=True, indent=2)
    short = plan.label.split(" ")[-1] if plan.label else req.name
    text = _replace_yaml_field(text, "short_name", short, quoted=True, indent=2)
    text = _replace_yaml_field(text, "seed", "false")
    pack_yaml.write_text(text, encoding="utf-8")

    env_path: Path | None = None
    env_written = False
    if req.write_env:
        env_path, env_written = _upsert_env_file(
            req=req,
            vault_path=plan.vault_path,
        )

    synthesis_applied = False
    synthesis_model: str | None = None
    synthesis_warning: str | None = None
    if req.synthesize_prompts and not req.from_seed:
        synthesis_applied, synthesis_model, synthesis_warning = (
            _maybe_synthesise_prompts(
                target=target,
                name=req.name,
                label=plan.label,
                description=plan.description,
                language=req.language,
            )
        )

    (plan.vault_path / "wiki").mkdir(parents=True, exist_ok=True)
    (plan.vault_path / "raw").mkdir(parents=True, exist_ok=True)
    # Boot-time mismatch detector (main.py:_check_vault_pack_marker) reads this.
    try:
        (plan.vault_path / ".pack-id").write_text(req.name + "\n", encoding="utf-8")
    except OSError:
        pass
    seed_vault(plan.vault_path, target, name=req.name, label=plan.label)

    return ScaffoldResult(
        name=req.name,
        target_pack_dir=target,
        vault_path=plan.vault_path,
        env_written=env_written,
        env_path=env_path,
        activated=bool(req.activate and env_written),
        requires_restart=True,
        next_steps=plan.next_steps,
        synthesis_applied=synthesis_applied,
        synthesis_model=synthesis_model,
        synthesis_warning=synthesis_warning,
    )


def _replace_yaml_field(
    text: str, key: str, value: str, *, quoted: bool = False, indent: int = 0
) -> str:
    pad = " " * indent
    pattern = re.compile(rf"^({re.escape(pad)}{re.escape(key)}:)[^\n]*$", re.MULTILINE)
    if quoted:
        safe = value.replace("\\", "\\\\").replace('"', '\\"')
        replacement = rf'\1 "{safe}"'
    else:
        replacement = rf"\1 {value}"
    return pattern.sub(replacement, text, count=1)


def _upsert_env_file(*, req: ScaffoldRequest, vault_path: Path) -> tuple[Path, bool]:
    """Upsert relevant keys into ``.env``. Preserves all unrelated content.

    Returns ``(path, written?)``. Never raises on permission errors —
    callers see ``written=False`` and can fall back to manual instructions.
    """
    # Lazy attribute lookup so tests that monkeypatch
    # ``llm_wiki.admin.scaffold.repo_root`` keep working — see
    # ``test_scaffold_activate_resets_pack_cache_and_syncs_env``.
    from llm_wiki.admin import scaffold as _pkg

    rr = _pkg.repo_root()
    env_path = rr / ".env"
    template = rr / ".env.example"

    def _mutate(base: str) -> str:
        if req.activate:
            base = _upsert_env_kv(base, "APP_DOMAIN", req.name)
        # Wiki SHARED (Fase 4): un solo `WIKI_ROOT` flat, valido per tutti
        # i pack. Niente più `WIKI_ROOT_<NAME>` per-pack — quella era una
        # reliquia del modello "ogni pack ha il proprio vault" pre-Fase 4.
        base = _upsert_env_kv(base, "WIKI_ROOT", str(vault_path))
        prov = req.provider
        if prov is not None:
            if prov.vendor:
                base = _upsert_env_kv(base, "LLM_VENDOR", prov.vendor)
            if prov.rag_vendor:
                base = _upsert_env_kv(base, "RAG_VENDOR", prov.rag_vendor)
            if prov.ingest_vendor:
                base = _upsert_env_kv(base, "INGEST_VENDOR", prov.ingest_vendor)
            eff_rag = prov.rag_vendor or prov.vendor
            eff_ingest = prov.ingest_vendor or prov.vendor
            if eff_rag == "ollama" and prov.model:
                base = _upsert_env_kv(base, "OLLAMA_MODEL", prov.model)
            elif eff_rag == "openai" and prov.model:
                base = _upsert_env_kv(base, "OPENAI_MODEL", prov.model)
            if eff_ingest == "ollama" and prov.ingest_model:
                base = _upsert_env_kv(base, "INGEST_OLLAMA_MODEL", prov.ingest_model)
            elif eff_ingest == "openai" and prov.ingest_model:
                base = _upsert_env_kv(base, "INGEST_OPENAI_MODEL", prov.ingest_model)
            if prov.ollama_url:
                base = _upsert_env_kv(base, "OLLAMA_URL", prov.ollama_url)
            if prov.openai_api_base:
                base = _upsert_env_kv(base, "OPENAI_API_BASE", prov.openai_api_base)
            if prov.openai_api_key:
                base = _upsert_env_kv(base, "OPENAI_API_KEY", prov.openai_api_key)
            if prov.base_url and not prov.ollama_url and not prov.openai_api_base:
                if "ollama" in {eff_rag, eff_ingest}:
                    base = _upsert_env_kv(base, "OLLAMA_URL", prov.base_url)
                if "openai" in {eff_rag, eff_ingest}:
                    base = _upsert_env_kv(base, "OPENAI_API_BASE", prov.base_url)
            if (
                prov.api_key
                and not prov.openai_api_key
                and "openai" in {eff_rag, eff_ingest}
            ):
                base = _upsert_env_kv(base, "OPENAI_API_KEY", prov.api_key)
        return base

    written = mutate_env_file(env_path, _mutate, template=template)
    if not written:
        return env_path, False

    # Sync into the live process so subsequent same-process reads (e.g. the
    # wizard's "Documenti" upload step that runs RIGHT after this) see the
    # new vault path without waiting for a restart. Only touches keys we
    # explicitly write — never overrides unrelated shell vars.
    if req.activate:
        _os.environ["APP_DOMAIN"] = req.name
    _os.environ["WIKI_ROOT"] = str(vault_path)

    try:
        from llm_wiki import config as _cfg

        _cfg.refresh_paths()
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("[scaffold] config.refresh_paths failed: %s", exc)

    prov = req.provider
    if prov is not None:
        if prov.vendor:
            _os.environ["LLM_VENDOR"] = prov.vendor
        if prov.rag_vendor:
            _os.environ["RAG_VENDOR"] = prov.rag_vendor
        if prov.ingest_vendor:
            _os.environ["INGEST_VENDOR"] = prov.ingest_vendor
        eff_rag = prov.rag_vendor or prov.vendor
        eff_ingest = prov.ingest_vendor or prov.vendor
        if eff_rag == "ollama" and prov.model:
            _os.environ["OLLAMA_MODEL"] = prov.model
        elif eff_rag == "openai" and prov.model:
            _os.environ["OPENAI_MODEL"] = prov.model
        if eff_ingest == "ollama" and prov.ingest_model:
            _os.environ["INGEST_OLLAMA_MODEL"] = prov.ingest_model
        elif eff_ingest == "openai" and prov.ingest_model:
            _os.environ["INGEST_OPENAI_MODEL"] = prov.ingest_model
        if prov.ollama_url:
            _os.environ["OLLAMA_URL"] = prov.ollama_url
        if prov.openai_api_base:
            _os.environ["OPENAI_API_BASE"] = prov.openai_api_base
        if prov.openai_api_key:
            _os.environ["OPENAI_API_KEY"] = prov.openai_api_key
        if prov.base_url and not prov.ollama_url and not prov.openai_api_base:
            if "ollama" in {eff_rag, eff_ingest}:
                _os.environ["OLLAMA_URL"] = prov.base_url
            if "openai" in {eff_rag, eff_ingest}:
                _os.environ["OPENAI_API_BASE"] = prov.base_url
        if (
            prov.api_key
            and not prov.openai_api_key
            and "openai" in {eff_rag, eff_ingest}
        ):
            _os.environ["OPENAI_API_KEY"] = prov.api_key
        try:
            from llm_wiki.utils.llm import reset_clients

            reset_clients()
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("[scaffold] reset_clients failed: %s", exc)

    if req.activate:
        try:
            from llm_wiki.domain.registry import reset_pack_cache

            reset_pack_cache()
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("[scaffold] reset_pack_cache failed: %s", exc)

    return env_path, True


def _next_steps(name: str, activated: bool) -> list[str]:
    base = [
        f"Tune domains/{name}/pack.yaml (page types, grouping, UI labels).",
        f"Customise domains/{name}/prompts/* for the vertical.",
        "Optional: rename strategies.py.example → strategies.py for per-page-type logic.",
    ]
    if activated:
        base.append("Restart the API: `python -m llm_wiki serve` (single-tenant boot).")
    else:
        base.append(
            f"To activate this pack: set APP_DOMAIN={name} in .env and restart the API."
        )
    return base
