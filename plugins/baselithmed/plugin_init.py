"""
Initialization helpers for :class:`BaselithMedPlugin`.

Each ``_setup_*`` function receives the plugin instance as its first argument
and mutates it in place, mirroring the original monolithic ``initialize``
body but split along responsibility seams to keep ``plugin.py`` ≤ 500 LOC.
"""

from __future__ import annotations

import os
from typing import Any

from core.observability.logging import get_logger

from .agents.anamnesis_agent import AnamnesisAgent
from .agents.clinical_reasoner import ClinicalReasoner
from .agents.differential_dx_agent import DifferentialDxAgent
from .audit import AuditLedger
from .ehr import EhrPushConfig, EhrPusher
from .flows.interview_flow import InterviewFlowHandler
from .flows.triage_flow import TriageFlowHandler
from .lexicons import DEFAULT_LANGUAGE, load_symptom_lexicon
from .persistence import SQLiteAuditBackend
from .providers.medgemma_ollama import OllamaMedGemmaProvider
from .retention import RetentionRunner
from .safety.redflags import RedFlagEvaluator
from .webhooks import WebhookConfig, WebhookDispatcher, WebhookTarget

logger = get_logger(__name__)


def _setup_retention(plugin: Any, config: dict[str, Any]) -> None:
    """Configure the data-retention policy from config / env vars."""
    retention_cfg = config.get("retention", {}) if isinstance(config, dict) else {}
    retention_days_raw = (
        retention_cfg.get("days") or os.getenv("BASELITHMED_RETENTION_DAYS") or 30
    )
    try:
        plugin._retention.retention_days = int(retention_days_raw)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid BASELITHMED_RETENTION_DAYS=%r; defaulting to 30.",
            retention_days_raw,
        )
        plugin._retention.retention_days = 30


def _setup_audit(plugin: Any, config: dict[str, Any]) -> None:
    """Wire the SQLite audit backend when configured; fall back to in-memory."""
    audit_cfg = config.get("audit", {}) if isinstance(config, dict) else {}
    audit_path = audit_cfg.get("sqlite_path") or os.getenv("BASELITHMED_AUDIT_DB_PATH")
    if not audit_path:
        return
    try:
        plugin._audit_backend = SQLiteAuditBackend(audit_path)
        plugin._audit = AuditLedger(backend=plugin._audit_backend)
        logger.info(
            "BaselithMed audit ledger persisted to SQLite: %s",
            audit_path,
        )
    except Exception as exc:  # noqa: BLE001 — degrade to in-memory
        logger.warning(
            "Failed to open SQLite audit backend %r (%s); "
            "continuing with in-memory ledger.",
            audit_path,
            exc,
        )


def _setup_ehr(plugin: Any, config: dict[str, Any]) -> None:
    """Configure the EHR pusher from config / env vars."""
    ehr_cfg_dict = config.get("ehr", {}) if isinstance(config, dict) else {}
    ehr_config: EhrPushConfig | None = None
    if ehr_cfg_dict.get("url"):
        try:
            ehr_config = EhrPushConfig.model_validate(ehr_cfg_dict)
        except Exception as exc:  # noqa: BLE001 — invalid config disables push
            logger.warning("BaselithMed EHR config invalid (%s); push disabled.", exc)
    if ehr_config is None:
        ehr_config = EhrPushConfig.from_env()
    if ehr_config is not None:
        plugin._ehr_pusher = EhrPusher(ehr_config)
        logger.info("BaselithMed EHR push enabled: %s", ehr_config.url)


def _setup_providers(plugin: Any, config: dict[str, Any]) -> None:
    """Instantiate main + optional fast LLM providers and set on plugin."""
    provider_cfg = config.get("provider", {}) if isinstance(config, dict) else {}
    host = provider_cfg.get("host") or os.getenv("BASELITHMED_OLLAMA_HOST")
    num_predict_raw = provider_cfg.get("num_predict")
    keep_alive = str(provider_cfg.get("keep_alive", "30m"))
    context_window = int(provider_cfg.get("context_window", 8192))
    temperature = float(provider_cfg.get("temperature", 0.2))

    # Main provider — quality-sensitive finalize DDx ranking.
    plugin._provider = OllamaMedGemmaProvider(
        api_base=host,
        model_id=(
            provider_cfg.get("model_id")
            or os.getenv("BASELITHMED_MODEL_ID")
            or "medgemma:4b"
        ),
        temperature=temperature,
        context_window=context_window,
        keep_alive=keep_alive,
        num_predict=int(num_predict_raw) if num_predict_raw else None,
    )

    # Optional fast provider — latency-sensitive per-turn extraction +
    # anamnesis questions. When ``fast_model_id`` is unset the main
    # provider is reused (single-model behaviour, fully backward-compat).
    fast_model_id = provider_cfg.get("fast_model_id") or os.getenv(
        "BASELITHMED_FAST_MODEL_ID"
    )
    if fast_model_id and fast_model_id != plugin._provider.model_id:
        plugin._fast_provider = OllamaMedGemmaProvider(
            api_base=host,
            model_id=str(fast_model_id),
            temperature=temperature,
            context_window=context_window,
            keep_alive=keep_alive,
            num_predict=int(num_predict_raw) if num_predict_raw else None,
        )
        logger.info(
            "BaselithMed dual-model: fast=%s, finalize=%s",
            fast_model_id,
            plugin._provider.model_id,
        )
    else:
        plugin._fast_provider = plugin._provider


def _setup_agents_and_handlers(plugin: Any, config: dict[str, Any]) -> None:
    """Create anamnesis / DDx / reasoner agents and flow handlers."""
    provider_cfg = config.get("provider", {}) if isinstance(config, dict) else {}

    # Per-turn LLM budget. With a fast model (~1-2s) keep it tight; with
    # only a big model (medgemma:27b, ~13-15s) raise it or every turn
    # falls back to the deterministic question/DDx bank.
    turn_timeout = float(
        provider_cfg.get("turn_timeout_seconds")
        or os.getenv("BASELITHMED_TURN_TIMEOUT_SECONDS")
        or 3.0
    )

    plugin._anamnesis_agent = AnamnesisAgent(
        provider=plugin._fast_provider,
        graph=plugin._graph_repo,
        turn_timeout_seconds=turn_timeout,
    )

    lang = (
        provider_cfg.get("language")
        or os.getenv("BASELITHMED_LANG")
        or DEFAULT_LANGUAGE
    )
    canonicalization_lexicon: tuple[tuple[str, str, str | None], ...] | None = None
    try:
        loaded = load_symptom_lexicon(lang)
        canonicalization_lexicon = loaded
        logger.info(
            "BaselithMed canonicalization lexicon: %s (%d entries)",
            lang,
            len(loaded),
        )
    except Exception as exc:  # noqa: BLE001 — fall back to default IT
        logger.warning(
            "BaselithMed lexicon load for %r failed (%s); using default Italian.",
            lang,
            exc,
        )

    plugin._dx_agent = DifferentialDxAgent(
        provider=plugin._provider,
        fast_provider=plugin._fast_provider,
        canonicalization_lexicon=canonicalization_lexicon,
        turn_timeout_seconds=turn_timeout,
    )

    # Hypothesis-driven clinical reasoner. Off by default for zero
    # regression; enable via ``reasoning.enabled`` in plugins.yaml. The
    # live loop uses the fast provider by default (latency-sensitive);
    # set ``reasoning.model: main`` to use the larger finalize model.
    reasoning_cfg = config.get("reasoning", {}) if isinstance(config, dict) else {}
    use_reasoner = bool(reasoning_cfg.get("enabled", False))
    reasoner_model = str(reasoning_cfg.get("model", "fast")).lower()
    reasoner_provider = (
        plugin._provider if reasoner_model == "main" else plugin._fast_provider
    )
    plugin._reasoner = ClinicalReasoner(
        provider=reasoner_provider,
        turn_timeout_seconds=turn_timeout,
    )
    if use_reasoner:
        logger.info(
            "BaselithMed hypothesis-driven reasoner ENABLED (model=%s).",
            reasoner_provider.model_id,
        )

    red_flags = RedFlagEvaluator()
    plugin.interview_handler = InterviewFlowHandler(
        anamnesis_agent=plugin._anamnesis_agent,
        dx_agent=plugin._dx_agent,
        graph=plugin._graph_repo,
        red_flags=red_flags,
        reasoner=plugin._reasoner,
        use_reasoner=use_reasoner,
    )
    plugin.triage_handler = TriageFlowHandler(
        dx_agent=plugin._dx_agent,
        graph=plugin._graph_repo,
        human=plugin._human,
        red_flags=red_flags,
    )

    # Late-bind so InterviewFlowHandler can finalize inline when the
    # anamnesis loop has no more slots to ask.
    plugin.interview_handler.set_triage_handler(plugin.triage_handler)


def _setup_retention_runner(plugin: Any, config: dict[str, Any]) -> None:
    """Start the background retention runner when a non-zero interval is set."""
    retention_cfg = config.get("retention", {}) if isinstance(config, dict) else {}
    runner_interval_raw = retention_cfg.get("runner_interval_seconds") or os.getenv(
        "BASELITHMED_RETENTION_RUNNER_INTERVAL_SECONDS"
    )
    try:
        runner_interval = float(runner_interval_raw) if runner_interval_raw else 0.0
    except (TypeError, ValueError):
        runner_interval = 0.0

    if runner_interval > 0:
        runner = RetentionRunner(
            plugin, plugin._retention, interval_seconds=runner_interval
        )
        runner.start()
        plugin._retention_runner = runner
        logger.info(
            "BaselithMed retention runner enabled (every %.0fs).",
            runner_interval,
        )


def _setup_webhooks(plugin: Any, config: dict[str, Any]) -> None:
    """Configure the webhook dispatcher from config / env vars."""
    webhook_cfg_raw = config.get("webhooks") if isinstance(config, dict) else None
    try:
        if isinstance(webhook_cfg_raw, dict) and webhook_cfg_raw.get("targets"):
            targets = [
                WebhookTarget.model_validate(t) for t in webhook_cfg_raw["targets"]
            ]
            plugin._webhooks = WebhookDispatcher(WebhookConfig(targets=targets))
        else:
            env_cfg = WebhookConfig.from_env()
            if env_cfg.targets:
                plugin._webhooks = WebhookDispatcher(env_cfg)
    except Exception as exc:  # noqa: BLE001 — disable webhooks on bad cfg
        logger.warning("BaselithMed webhook config invalid (%s).", exc)

    if plugin._webhooks.enabled:
        logger.info(
            "BaselithMed webhooks enabled: %d target(s).",
            len(plugin._webhooks._config.targets),
        )
