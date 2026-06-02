"""Domain-aware prompt synthesis hook (LLM-driven, non-fatal on failure)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_wiki.admin.vault_seed import read_pack_data

logger = logging.getLogger(__name__)


def _maybe_synthesise_prompts(
    *,
    target: Path,
    name: str,
    label: str,
    description: str,
    language: str,
) -> tuple[bool, str | None, str | None]:
    """Run the LLM-backed synthesizer and persist its output.

    Returns ``(applied, model_id, warning)``. On any failure returns
    ``(False, None, "<reason>")`` — the bare ``_template`` files are
    left untouched and the warning surfaces in :class:`ScaffoldResult`
    so the wizard / CLI can show it to the user.
    """
    try:
        from llm_wiki.admin.prompt_synthesizer import (
            BASELINE_NO_HITS_J2,
            BASELINE_SYSTEM_J2,
            SynthesisError,
            synthesize_pack,
        )
    except Exception as exc:  # missing optional dep, import-time failure
        logger.warning("[synthesis] synthesizer unavailable: %s", exc)
        return False, None, f"synthesizer unavailable: {exc}"

    pack_data = read_pack_data(target)
    page_types = list(pack_data.get("page_types") or [])
    if not page_types:
        logger.warning(
            "[synthesis] %s has no page_types in pack.yaml — skipping synthesis", name
        )
        return False, None, "pack.yaml has no page_types"

    try:
        result = synthesize_pack(
            name=name,
            label=label,
            description=description,
            language=language,
            page_types=page_types,
        )
    except Exception as exc:
        is_known = isinstance(exc, SynthesisError)
        level = logging.WARNING if is_known else logging.ERROR
        logger.log(
            level, "[synthesis] failed for %s: %s", name, exc, exc_info=not is_known
        )
        return False, None, str(exc) or exc.__class__.__name__

    prompts_dir = target / "prompts"
    try:
        _write_with_trailing_nl(
            prompts_dir / "system.j2", BASELINE_SYSTEM_J2 + result.system_prompt
        )
        _write_with_trailing_nl(
            prompts_dir / "no_hits.j2", BASELINE_NO_HITS_J2 + result.no_hits
        )
        _patch_pack_yaml_with_synthesis(
            pack_yaml=target / "pack.yaml",
            disclaimer=result.disclaimer,
            subtypes=result.subtypes,
            suggested_questions=[q.model_dump() for q in result.suggested_questions],
        )
        meta = {
            "model": result.model,
            "vendor": result.vendor,
            "name": name,
            "label": label,
            "description": description,
            "language": language,
            "page_type_folders": [
                pt.get("folder") or pt.get("plural") or pt.get("id")
                for pt in page_types
            ],
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        (prompts_dir / ".synth.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        logger.error("[synthesis] persist failed for %s: %s", name, exc)
        return False, None, f"persistence failed: {exc}"

    logger.info("[synthesis] applied to %s via %s", name, result.model)
    return True, result.model, None


def _write_with_trailing_nl(path: Path, content: str) -> None:
    text = content if content.endswith("\n") else content + "\n"
    path.write_text(text, encoding="utf-8")


def _patch_pack_yaml_with_synthesis(
    *,
    pack_yaml: Path,
    disclaimer: str,
    subtypes: dict[str, list[str]],
    suggested_questions: list[dict[str, Any]],
) -> None:
    """Round-trip ``pack.yaml`` to inject the synthesised UI fields.

    Comments in the file are dropped — acceptable for user-scaffolded
    packs (the comment block in ``_template`` is scaffold-time guidance,
    not runtime documentation). Field ordering is preserved by relying
    on the dict-insertion order already established by the loader.
    """
    import yaml  # local import — keep CLI surface tight

    raw = pack_yaml.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise OSError(f"{pack_yaml} is not a YAML mapping; refusing to patch")

    if subtypes:
        data["subtypes"] = subtypes

    ui = data.get("ui")
    if not isinstance(ui, dict):
        ui = {}
        data["ui"] = ui
    ui["disclaimer"] = disclaimer
    if suggested_questions:
        ui["suggested_questions"] = suggested_questions

    pack_yaml.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=10**6),
        encoding="utf-8",
    )
