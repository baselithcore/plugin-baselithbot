"""Sandbox-driven probe runner and corpus path helper.

Drives a payload corpus end-to-end through the sandbox, enforcing the
rate-limit and consecutive-5xx / consecutive-refusal stop conditions.
"""

from __future__ import annotations

import asyncio
import json
from importlib import resources
from pathlib import Path
from typing import Iterable

from core.observability.tracing import get_tracer
from plugins.red_agent.metrics import (
    LLM_PROBE_FINDINGS_TOTAL,
    LLM_PROBE_HALTED_TOTAL,
    LLM_PROBE_REQUESTS_TOTAL,
)
from plugins.red_agent.models import Target
from plugins.red_agent.sandbox_runner import SandboxRunner
from plugins.red_agent.scanners._llm_probe._findings import make_finding
from plugins.red_agent.scanners._llm_probe._http import (
    build_curl_argv,
    build_request_body,
    detect_outcome,
    extract_response_text,
    parse_curl_output,
    substitute_sentinel,
)
from plugins.red_agent.scanners._llm_probe._models import (
    PayloadEntry,
    ProbeRun,
    TargetConfig,
)

_tracer = get_tracer("red_agent.scanner")


async def run_probes(
    *,
    scanner_name: str,
    sandbox: SandboxRunner,
    image: str,
    timeout: int,
    target: Target,
    payloads: Iterable[PayloadEntry],
) -> ProbeRun:
    """Drive the corpus end-to-end inside the sandbox.

    Walks each payload, builds the request, executes via the sandbox,
    parses the response, applies detection, enforces stop conditions,
    and rate-limits between calls. Caller wires the scanner-specific
    ``image`` and per-corpus ``payloads``.
    """

    cfg = TargetConfig.from_target(target)
    run = ProbeRun()
    payloads = list(payloads)
    with _tracer.start_span(
        "red_agent.scanner.llm_probe",
        attributes={
            "scanner.name": scanner_name,
            "scanner.endpoint": cfg.chat_endpoint,
            "scanner.payloads": len(payloads),
        },
    ) as span:
        for payload in payloads:
            prompt = substitute_sentinel(payload.prompt, cfg.system_prompt_sentinel)
            body = build_request_body(cfg.request_template, prompt)
            argv = build_curl_argv(cfg, body)
            try:
                result = await sandbox.execute(
                    image=image,
                    argv=argv,
                    timeout=timeout,
                    network=True,
                    scanner=scanner_name,
                )
            except Exception as exc:  # noqa: BLE001
                run.halted_reason = f"sandbox_error: {exc}"
                LLM_PROBE_REQUESTS_TOTAL.labels(
                    scanner=scanner_name, result="sandbox_error"
                ).inc()
                LLM_PROBE_HALTED_TOTAL.labels(
                    scanner=scanner_name, reason="sandbox_error"
                ).inc()
                break
            run.sent += 1
            status, body_text = parse_curl_output(result.stdout)
            if 500 <= status < 600 or status == 0:
                run.consecutive_5xx += 1
                LLM_PROBE_REQUESTS_TOTAL.labels(
                    scanner=scanner_name, result="5xx"
                ).inc()
                if run.consecutive_5xx >= cfg.max_consecutive_5xx:
                    run.halted_reason = (
                        f"consecutive_5xx>={cfg.max_consecutive_5xx} "
                        f"(last_status={status})"
                    )
                    LLM_PROBE_HALTED_TOTAL.labels(
                        scanner=scanner_name, reason="consecutive_5xx"
                    ).inc()
                    break
                await _sleep(cfg.rate_limit_seconds)
                continue
            run.consecutive_5xx = 0
            LLM_PROBE_REQUESTS_TOTAL.labels(scanner=scanner_name, result="ok").inc()

            try:
                parsed = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError:
                parsed = body_text
            text = extract_response_text(parsed, cfg.response_path)
            outcome = detect_outcome(text, payload, sentinel=cfg.system_prompt_sentinel)
            if outcome.detected:
                run.consecutive_refusals = 0
                run.findings.append(
                    make_finding(
                        scanner_name=scanner_name,
                        target=target,
                        cfg=cfg,
                        payload=payload,
                        outcome=outcome,
                        request_body=body,
                        response_status=status,
                        response_text=text,
                    )
                )
                LLM_PROBE_FINDINGS_TOTAL.labels(
                    scanner=scanner_name,
                    outcome=outcome.outcome or "unknown",
                    category=payload.category,
                ).inc()
            elif outcome.refusal:
                run.consecutive_refusals += 1
                if run.consecutive_refusals >= cfg.max_consecutive_refusals:
                    run.halted_reason = (
                        f"consecutive_refusals>={cfg.max_consecutive_refusals} "
                        "(target hardened)"
                    )
                    LLM_PROBE_HALTED_TOTAL.labels(
                        scanner=scanner_name, reason="hardened_target"
                    ).inc()
                    break
            else:
                run.consecutive_refusals = 0

            await _sleep(cfg.rate_limit_seconds)
        span.set_attribute("scanner.findings", len(run.findings))
        span.set_attribute("scanner.requests_sent", run.sent)
        if run.halted_reason:
            span.set_attribute("scanner.halted_reason", run.halted_reason)
    return run


async def _sleep(seconds: float) -> None:
    if seconds > 0:
        await asyncio.sleep(seconds)


def corpus_path(filename: str) -> Path:
    """Helper for tests: filesystem path to a packaged corpus."""

    pkg = resources.files("plugins.red_agent.scanners.llm_payloads")
    return Path(str(pkg / filename))
