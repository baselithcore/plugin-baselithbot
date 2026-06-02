"""Data types and corpus loading for the LLM Top 10 probes.

Defines the immutable ``PayloadEntry``, the per-run ``ProbeOutcome`` /
``ProbeRun`` state, the resolved ``TargetConfig`` view over
``Target.metadata``, and the YAML corpus loader.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources

import yaml

from plugins.red_agent.models import Finding, Severity, Target

DEFAULT_CWE = "CWE-1426"
DEFAULT_REFUSAL_MARKERS: tuple[str, ...] = (
    "i cannot",
    "i can't",
    "i won't",
    "i am not able",
    "i'm not able",
    "i won't be able",
    "i must decline",
    "i'm sorry, but",
    "as an ai",
    "not appropriate",
    "against my",
    "i refuse",
)
SENTINEL_PLACEHOLDER = "{{SENTINEL}}"


@dataclass(frozen=True)
class PayloadEntry:
    """One probe entry parsed from a YAML corpus."""

    id: str
    category: str
    severity: Severity
    cwe: str
    prompt: str
    detect: dict[str, list[str]]
    refusal_markers: tuple[str, ...]
    source: dict[str, str]


@dataclass
class ProbeOutcome:
    """Detection result for a single payload."""

    payload_id: str
    detected: bool
    outcome: str | None = None
    matched: list[str] = field(default_factory=list)
    refusal: bool = False
    response_excerpt: str = ""


@dataclass
class ProbeRun:
    """Aggregate state for a scanner run.

    Carries the running counters used by stop conditions so callers can
    inspect why a probe halted mid-corpus.
    """

    findings: list[Finding] = field(default_factory=list)
    consecutive_5xx: int = 0
    consecutive_refusals: int = 0
    sent: int = 0
    halted_reason: str | None = None


def load_payloads(filename: str) -> list[PayloadEntry]:
    """Load and validate a YAML payload corpus from this package."""

    raw = _read_corpus(filename)
    entries: list[PayloadEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"payload entry must be a mapping, got {type(item)!r}")
        entries.append(_coerce_entry(item))
    return entries


def _read_corpus(filename: str) -> list[dict]:
    pkg = resources.files("plugins.red_agent.scanners.llm_payloads")
    text = (pkg / filename).read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)
    if not isinstance(parsed, list):
        raise ValueError(f"corpus {filename} must be a YAML list at the top level")
    return parsed


def _coerce_entry(item: dict) -> PayloadEntry:
    detect_raw = item.get("detect") or {}
    if not isinstance(detect_raw, dict):
        raise ValueError(f"detect must be a mapping in payload {item.get('id')!r}")
    detect: dict[str, list[str]] = {}
    for outcome, markers in detect_raw.items():
        if not isinstance(markers, list):
            raise ValueError(f"detect.{outcome} must be a list of strings")
        detect[str(outcome)] = [str(m) for m in markers]
    refusal_markers_raw = item.get("refusal_markers")
    if refusal_markers_raw is None:
        refusal_markers: tuple[str, ...] = DEFAULT_REFUSAL_MARKERS
    else:
        refusal_markers = tuple(str(m).lower() for m in refusal_markers_raw)
    severity_raw = (item.get("severity") or "high").lower()
    try:
        severity = Severity(severity_raw)
    except ValueError as exc:
        raise ValueError(f"unknown severity {severity_raw!r}") from exc
    return PayloadEntry(
        id=str(item["id"]),
        category=str(item.get("category") or "uncategorized"),
        severity=severity,
        cwe=str(item.get("cwe") or DEFAULT_CWE),
        prompt=str(item["prompt"]),
        detect=detect,
        refusal_markers=refusal_markers,
        source=dict(item.get("source") or {}),
    )


@dataclass
class TargetConfig:
    """Resolved view of ``Target.metadata`` for one scan."""

    chat_endpoint: str
    request_template: dict
    response_path: tuple[str, ...]
    auth_header_name: str
    auth_token: str
    system_prompt_sentinel: str
    rate_limit_seconds: float
    max_consecutive_5xx: int
    max_consecutive_refusals: int

    @classmethod
    def from_target(cls, target: Target) -> "TargetConfig":
        meta = target.metadata or {}
        endpoint = meta.get("chat_endpoint") or target.value
        if not endpoint or not str(endpoint).lower().startswith(
            ("http://", "https://")
        ):
            raise ValueError("target.metadata.chat_endpoint must be an http(s) URL")
        template = meta.get("request_template") or {
            "model": meta.get("model", "default"),
            "messages": [{"role": "user", "content": "{prompt}"}],
        }
        if not isinstance(template, dict):
            raise ValueError("request_template must be a JSON object")
        path_raw = meta.get("response_path") or "choices.0.message.content"
        return cls(
            chat_endpoint=str(endpoint),
            request_template=template,
            response_path=tuple(str(path_raw).split(".")),
            auth_header_name=str(meta.get("auth_header_name") or "Authorization"),
            auth_token=str(meta.get("auth_token") or ""),
            system_prompt_sentinel=str(meta.get("system_prompt_sentinel") or ""),
            rate_limit_seconds=float(meta.get("rate_limit_seconds", 1.0)),
            max_consecutive_5xx=int(meta.get("max_consecutive_5xx", 5)),
            max_consecutive_refusals=int(meta.get("max_consecutive_refusals", 10)),
        )
