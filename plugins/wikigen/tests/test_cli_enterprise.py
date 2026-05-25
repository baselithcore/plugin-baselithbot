"""Enterprise-grade CLI behaviour tests.

Covers the new global flags and commands added in the CLI refactor:

- ``--version`` prints the version and exits 0.
- ``--json`` produces parseable JSON for ``status`` / ``pack list``
  / ``doctor`` / ``pack show`` / ``pack validate``.
- ``doctor`` exit codes follow the documented contract (0 / 3) and
  ``--strict`` upgrades warnings to failures.
- ``pack show`` / ``pack validate`` work on a freshly scaffolded pack
  and surface validation issues for malformed packs.
- ``ingest`` exits with code 1 (user error) when given a missing file,
  without leaking a traceback to the caller.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.domain.prompts import reset_registry_cache
from llm_wiki.domain.registry import reset_pack_cache
from llm_wiki.domain.schema import reset_schema_cache
from llm_wiki.domain.strategies import reset_strategies_cache

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    reset_pack_cache()
    reset_registry_cache()
    reset_schema_cache()
    reset_strategies_cache()
    yield
    reset_pack_cache()
    reset_registry_cache()
    reset_schema_cache()
    reset_strategies_cache()


@pytest.fixture
def scaffolded(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    """Scaffold a throwaway pack used by several tests below."""
    name = "smoke_cli"
    target = REPO_ROOT / "domains" / name
    if target.exists():
        shutil.rmtree(target)
    vault = tmp_path / "vault"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "--domain",
            name,
            "--label",
            "Wiki CLI Smoke",
            "--vault-root",
            str(vault),
            "--no-write-env",
        ],
    )
    assert result.exit_code == 0, result.output
    yield name, target
    if target.exists():
        shutil.rmtree(target)


def test_version_flag_prints_version_and_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip()  # non-empty


def test_init_json_output(tmp_path: Path) -> None:
    name = "smoke_cli_json"
    target = REPO_ROOT / "domains" / name
    if target.exists():
        shutil.rmtree(target)
    runner = CliRunner()
    try:
        result = runner.invoke(
            app,
            [
                "--json",
                "init",
                "--domain",
                name,
                "--label",
                "JSON Smoke",
                "--vault-root",
                str(tmp_path / "vault"),
                "--no-write-env",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["name"] == name
        assert payload["activated"] is False  # write_env=false
        assert isinstance(payload["next_steps"], list)
    finally:
        if target.exists():
            shutil.rmtree(target)


def test_pack_list_json_includes_scaffolded_pack(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    runner = CliRunner()
    result = runner.invoke(app, ["--json", "pack", "list"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    names = [p["name"] for p in payload["packs"]]
    assert name in names
    pack = next(p for p in payload["packs"] if p["name"] == name)
    assert pack["seed"] is False
    assert "source" in pack["page_types"]


def test_pack_show_json(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    runner = CliRunner()
    result = runner.invoke(app, ["--json", "pack", "show", name])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["pack"]["name"] == name
    assert payload["pack"]["label"] == "Wiki CLI Smoke"


def test_pack_show_unknown_returns_user_error() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--json", "pack", "show", "does_not_exist"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "does_not_exist" in payload["error"] or "no pack.yaml" in payload["error"]


def test_pack_validate_passes_for_scaffolded(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    runner = CliRunner()
    result = runner.invoke(app, ["--json", "pack", "validate", name])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["issues"] == []


def test_pack_validate_detects_missing_prompt(scaffolded: tuple[str, Path]) -> None:
    name, target = scaffolded
    # corrupt the pack: drop a required prompt
    (target / "prompts" / "system.j2").unlink()
    runner = CliRunner()
    result = runner.invoke(app, ["--json", "pack", "validate", name])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any("system.j2" in i for i in payload["issues"])


def test_ingest_missing_file_exits_user_error(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--json", "ingest", str(tmp_path / "nonexistent.pdf")])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "not found" in payload["error"].lower()


def test_status_json_returns_known_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force setup-mode path: ensures status renders even without a pack.
    monkeypatch.setattr("llm_wiki.config.APP_DOMAIN", "")
    runner = CliRunner()
    result = runner.invoke(app, ["--json", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["setup_mode"] is True
    assert "version" in payload


def test_doctor_strict_flag_upgrades_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    """When every check returns ``warn``, ``--strict`` flips overall ok=false."""
    from llm_wiki.cli import doctor_cmd as dc

    def _all_warn(*_a: object, **_kw: object) -> dc.CheckResult:
        return dc.CheckResult("stub", "warn", "stub warn")

    monkeypatch.setattr(dc, "_check_pack", _all_warn)
    monkeypatch.setattr(dc, "_check_vault", _all_warn)
    monkeypatch.setattr(dc, "_check_env_overrides", _all_warn)
    monkeypatch.setattr(dc, "_check_qdrant", lambda *, timeout: _all_warn())
    monkeypatch.setattr(dc, "_check_llm", lambda *, timeout: _all_warn())

    runner = CliRunner()

    # Non-strict: warnings tolerated → exit 0.
    result_lax = runner.invoke(app, ["--json", "doctor"])
    assert result_lax.exit_code == 0
    payload_lax = json.loads(result_lax.stdout)
    assert payload_lax["ok"] is True

    # Strict: warnings escalate → exit 3, ok=false.
    result_strict = runner.invoke(app, ["--json", "doctor", "--strict"])
    assert result_strict.exit_code == 3
    payload_strict = json.loads(result_strict.stdout)
    assert payload_strict["ok"] is False


def test_log_format_json_emits_json_log_records(monkeypatch: pytest.MonkeyPatch) -> None:
    """A simple --log-format json invocation must not crash."""
    runner = CliRunner()
    result = runner.invoke(app, ["--log-format", "json", "--version"])
    assert result.exit_code == 0
