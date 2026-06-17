"""Read-only diagnostics projected from the framework CLI.

* ``doctor`` reuses the CLI's own connectivity checks
  (:mod:`core.cli.commands.doctor`) verbatim — single source of truth for
  infrastructure health.
* ``verify``/``info``/``config`` are re-derived here over stdlib + ``core.config``
  rather than scraping the CLI's Rich tables (those commands render only to a
  terminal); the underlying capabilities — import checks and the config getters —
  are reused directly.

All entry points run blocking work in a worker thread.
"""

from __future__ import annotations

import asyncio
import platform
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from ...cli_models import (
    CliCheck,
    ConfigItem,
    ConfigReport,
    ConfigSection,
    DoctorReport,
    InfoReport,
    VerifyItem,
    VerifyReport,
)

_WARN_CHECKS = ("GraphDB", "Plugins")
_CORE_MODULES = (
    ("core.di", "Dependency Injection"),
    ("core.config", "Configuration"),
    ("core.interfaces", "Service Protocols"),
    ("core.services.llm", "LLM Service"),
    ("core.services.vectorstore", "VectorStore Service"),
    ("core.services.chat", "Chat Service"),
    ("core.plugins", "Plugin System"),
)
_REQUIRED_DEPS = (
    ("fastapi", "FastAPI"),
    ("pydantic", "Pydantic"),
    ("pydantic_settings", "Pydantic Settings"),
)
_OPTIONAL_DEPS = (
    ("sentence_transformers", "Sentence Transformers (Reranker)"),
    ("qdrant_client", "Qdrant Client (Vector DB)"),
    ("langchain_text_splitters", "LangChain Text Splitters (Chunking)"),
)
_DIRECTORIES = ("plugins", "data", "documents", "configs")
_KNOWN_PROVIDERS = ("ollama", "openai", "anthropic", "huggingface")


def _doctor_sync() -> DoctorReport:
    from core.cli.commands.doctor import (  # local import: pulls rich/core lazily
        check_env_file,
        check_graph_db,
        check_llm_provider,
        check_plugins,
        check_postgres,
        check_qdrant,
        check_redis,
    )

    started = time.perf_counter()
    raw = [
        check_env_file(),
        check_llm_provider(),
        check_redis(),
        check_qdrant(),
        check_postgres(),
        check_graph_db(),
        check_plugins(),
    ]
    checks: list[CliCheck] = []
    passed = warnings = failed = 0
    for c in raw:
        if c.passed:
            severity = "pass"
            passed += 1
        elif c.name in _WARN_CHECKS:
            severity = "warn"
            warnings += 1
        else:
            severity = "fail"
            failed += 1
        checks.append(
            CliCheck(
                name=c.name,
                passed=c.passed,
                severity=severity,
                message=c.message,
                details=c.details,
            )
        )
    return DoctorReport(
        passed=passed,
        warnings=warnings,
        failed=failed,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        checks=checks,
    )


def _verify_sync() -> VerifyReport:
    started = time.perf_counter()
    items: list[VerifyItem] = []
    passed = warnings = failed = 0

    py = sys.version_info
    py_str = f"{py.major}.{py.minor}.{py.micro}"
    if py >= (3, 12):
        passed += 1
        items.append(
            VerifyItem(
                status="pass",
                category="System",
                component="Python Version",
                details=py_str,
            )
        )
    else:
        failed += 1
        items.append(
            VerifyItem(
                status="fail",
                category="System",
                component="Python Version",
                details=f"{py_str} (requires 3.12+)",
            )
        )

    for module, name in _CORE_MODULES:
        try:
            __import__(module)
            passed += 1
            items.append(VerifyItem(status="pass", category="Core", component=name))
        except ImportError as exc:
            failed += 1
            items.append(
                VerifyItem(
                    status="fail", category="Core", component=name, details=str(exc)
                )
            )

    for module, name in _REQUIRED_DEPS:
        try:
            __import__(module)
            passed += 1
            items.append(
                VerifyItem(status="pass", category="Dependency", component=name)
            )
        except ImportError:
            failed += 1
            items.append(
                VerifyItem(
                    status="fail",
                    category="Dependency",
                    component=name,
                    details="Not installed",
                )
            )

    for module, name in _OPTIONAL_DEPS:
        try:
            __import__(module)
            items.append(VerifyItem(status="pass", category="Optional", component=name))
        except ImportError:
            warnings += 1
            items.append(
                VerifyItem(
                    status="warn",
                    category="Optional",
                    component=name,
                    details="Not installed",
                )
            )

    for dir_name in _DIRECTORIES:
        if Path(dir_name).exists():
            items.append(
                VerifyItem(
                    status="pass",
                    category="Directory",
                    component=dir_name,
                    details="Found",
                )
            )
        else:
            warnings += 1
            items.append(
                VerifyItem(
                    status="warn",
                    category="Directory",
                    component=dir_name,
                    details="Not found",
                )
            )

    return VerifyReport(
        passed=passed,
        warnings=warnings,
        failed=failed,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        checks=items,
    )


def _info_sync() -> InfoReport:
    from core import __version__ as core_version

    try:
        fw_version = version("baselith-core")
    except PackageNotFoundError:
        fw_version = core_version

    project_name = "N/A"
    detected = False
    pyproject = Path.cwd() / "pyproject.toml"
    if pyproject.exists():
        detected = True
        try:
            for line in pyproject.read_text().splitlines():
                if line.startswith("name = "):
                    project_name = line.split("=")[1].strip().strip('"').strip("'")
                    break
        except Exception:  # noqa: BLE001 — best-effort metadata read
            project_name = "Unknown"

    plugins_dir = Path.cwd() / "plugins"
    plugin_count = (
        len(
            [
                p
                for p in plugins_dir.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ]
        )
        if plugins_dir.exists()
        else 0
    )
    return InfoReport(
        framework_version=str(fw_version),
        python=platform.python_version(),
        os=f"{platform.system()} {platform.release()}",
        project_name=project_name,
        project_detected=detected,
        plugin_count=plugin_count,
        project_path=str(Path.cwd()),
    )


def _section(name: str, title: str, getter: Any, rows: Any) -> ConfigSection:
    """Build one config section, degrading to an error section on failure."""
    try:
        cfg = getter()
    except Exception as exc:  # noqa: BLE001 — surfaced per-section
        return ConfigSection(name=name, title=title, available=False, error=str(exc))
    items = [ConfigItem(key=k, value=str(v)) for k, v in rows(cfg)]
    return ConfigSection(name=name, title=title, items=items)


def _config_sync() -> ConfigReport:
    from core.config import (  # local import keeps module import cheap
        get_chat_config,
        get_core_config,
        get_llm_config,
        get_vectorstore_config,
    )

    sections = [
        _section(
            "core",
            "Core",
            get_core_config,
            lambda c: [
                ("Log Level", c.log_level),
                ("Debug", c.debug),
                ("Plugin Dir", c.plugin_dir),
                ("Data Dir", c.data_dir),
            ],
        ),
        _section(
            "llm",
            "LLM",
            get_llm_config,
            lambda c: [
                ("Provider", c.provider),
                ("Model", c.model),
                (
                    "Cache",
                    getattr(c, "cache_enabled", getattr(c, "enable_cache", "N/A")),
                ),
            ],
        ),
        _section(
            "chat",
            "Chat",
            get_chat_config,
            lambda c: [
                ("Streaming", c.streaming_enabled),
                ("Initial Search K", c.initial_search_k),
                ("Final Top K", c.final_top_k),
            ],
        ),
        _section(
            "vectorstore",
            "Vector Store",
            get_vectorstore_config,
            lambda c: [
                ("Provider", c.provider),
                ("Host", getattr(c, "qdrant_host", getattr(c, "host", "N/A"))),
                ("Port", getattr(c, "qdrant_port", getattr(c, "port", "N/A"))),
            ],
        ),
    ]

    validation: list[CliCheck] = []
    valid = True
    for sec in sections:
        if sec.available:
            note = ""
            if sec.name == "llm":
                provider = next((i.value for i in sec.items if i.key == "Provider"), "")
                if provider and provider not in _KNOWN_PROVIDERS:
                    note = f"Unknown provider: {provider}"
            validation.append(
                CliCheck(
                    name=sec.title,
                    passed=True,
                    severity="warn" if note else "pass",
                    message=note or "Config valid",
                )
            )
        else:
            valid = False
            validation.append(
                CliCheck(
                    name=sec.title,
                    passed=False,
                    severity="fail",
                    message=sec.error or "Config error",
                )
            )
    return ConfigReport(valid=valid, sections=sections, validation=validation)


async def doctor() -> DoctorReport:
    """Run ``baselith doctor`` connectivity checks off-thread."""
    return await asyncio.to_thread(_doctor_sync)


async def verify() -> VerifyReport:
    """Run ``baselith verify`` installation checks off-thread."""
    return await asyncio.to_thread(_verify_sync)


async def info() -> InfoReport:
    """Build the ``baselith info`` snapshot off-thread."""
    return await asyncio.to_thread(_info_sync)


async def config_report() -> ConfigReport:
    """Build the ``baselith config show`` + ``validate`` view off-thread."""
    return await asyncio.to_thread(_config_sync)


__all__ = ["doctor", "verify", "info", "config_report"]
