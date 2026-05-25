"""Tests for the Sigma rule YAML emitter + HTTP endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.red_agent import dependencies as deps
from plugins.red_agent.exporters import to_sigma_dict, to_sigma_yaml
from plugins.red_agent.models import Finding, Severity
from plugins.red_agent.routers import findings_router


def _finding(*, with_guidance: bool = True, **kwargs: Any) -> Finding:
    base: dict[str, Any] = {
        "scanner": "nuclei",
        "title": "SQL injection",
        "description": "input not sanitized",
        "severity": Severity.HIGH,
        "target": "https://example.com",
        "cwe": "CWE-89",
    }
    base.update(kwargs)
    f = Finding(**base)
    if with_guidance:
        f.evidence = {
            "detection_guidance": {
                "logsource": {"product": "webserver", "category": "webserver"},
                "detection": "Look for `UNION SELECT` and `OR 1=1` payloads.",
                "mitigations": ["Use prepared statements"],
            },
            "attack_techniques": [
                {"id": "T1190", "name": "Exploit Public-Facing Application"},
            ],
        }
    return f


def test_no_guidance_returns_none() -> None:
    f = _finding(with_guidance=False)
    f.evidence = {}
    assert to_sigma_dict(f) is None
    assert to_sigma_yaml(f) is None


def test_dict_has_required_sigma_fields() -> None:
    rule = to_sigma_dict(_finding())
    assert rule is not None
    for key in (
        "title",
        "id",
        "status",
        "description",
        "logsource",
        "detection",
        "level",
    ):
        assert key in rule
    assert rule["detection"]["condition"] == "selection"
    assert rule["level"] == "high"


def test_keywords_extracted_from_backticked_tokens() -> None:
    rule = to_sigma_dict(_finding())
    assert rule is not None
    keywords = rule["detection"]["selection"]["keywords"]
    assert "UNION SELECT" in keywords
    assert "OR 1=1" in keywords


def test_attack_and_cwe_tags_emitted() -> None:
    rule = to_sigma_dict(_finding())
    assert rule is not None
    tags = rule.get("tags", [])
    assert "attack.t1190" in tags
    assert "cwe.cwe-89" in tags


def test_yaml_round_trip_parses() -> None:
    body = to_sigma_yaml(_finding())
    assert body is not None
    parsed = yaml.safe_load(body)
    assert parsed["status"] == "experimental"


def test_scanner_logsource_overrides_cwe_lane() -> None:
    f = _finding(scanner="nmap")
    rule = to_sigma_dict(f)
    assert rule is not None
    assert rule["logsource"] == {"product": "zeek", "category": "network_connection"}
    assert "baselithcore.scanner.nmap" in rule["tags"]


def test_unknown_scanner_keeps_cwe_logsource() -> None:
    f = _finding(scanner="custom-scanner")
    rule = to_sigma_dict(f)
    assert rule is not None
    assert rule["logsource"] == {"product": "webserver", "category": "webserver"}


def test_gitleaks_emits_file_event_logsource() -> None:
    f = _finding(scanner="gitleaks")
    rule = to_sigma_dict(f)
    assert rule is not None
    assert rule["logsource"]["category"] == "file_event"
    assert "baselithcore.scanner.gitleaks" in rule["tags"]


def test_keyword_override_replaces_extracted_tokens() -> None:
    rule = to_sigma_dict(_finding(), keyword_override=["SLEEP(", "BENCHMARK("])
    assert rule is not None
    assert rule["detection"]["selection"]["keywords"] == ["SLEEP(", "BENCHMARK("]


def test_keyword_override_dedupes_and_trims() -> None:
    rule = to_sigma_dict(_finding(), keyword_override=["  foo ", "foo", "", "bar"])
    assert rule is not None
    assert rule["detection"]["selection"]["keywords"] == ["foo", "bar"]


def test_extra_tags_appended_normalized() -> None:
    rule = to_sigma_dict(_finding(), extra_tags=["Team.AppSec", "  Q2.Campaign  "])
    assert rule is not None
    assert "team.appsec" in rule["tags"]
    assert "q2.campaign" in rule["tags"]


def test_http_keyword_query_overrides_keywords(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    f = _finding()
    f.discovered_at = datetime(2026, 4, 29, tzinfo=timezone.utc)
    p.findings[f.id] = (f, uuid4())
    resp = client.get(f"/findings/{f.id}/sigma?keyword=SLEEP(&keyword=BENCHMARK(")
    assert resp.status_code == 200
    parsed = yaml.safe_load(resp.text)
    assert parsed["detection"]["selection"]["keywords"] == ["SLEEP(", "BENCHMARK("]


def test_severity_mapping() -> None:
    rule = to_sigma_dict(_finding(severity=Severity.CRITICAL))
    assert rule is not None
    assert rule["level"] == "critical"
    rule = to_sigma_dict(_finding(severity=Severity.LOW))
    assert rule is not None
    assert rule["level"] == "low"


# ── HTTP endpoint ──────────────────────────────────────────────────────


class _StubPersistence:
    available = True

    def __init__(self) -> None:
        self.dsn = "stub"
        self.findings: dict[UUID, tuple[Finding, UUID]] = {}

    async def get_finding(self, finding_id: UUID) -> tuple[Finding, UUID] | None:
        return self.findings.get(finding_id)

    async def list_scan_audit(
        self, scan_id: UUID, *, limit: int = 500
    ) -> list[dict[str, Any]]:
        del scan_id, limit
        return []


class _StubAgent:
    def __init__(self, persistence: _StubPersistence) -> None:
        self.persistence = persistence


@pytest.fixture()
def http() -> tuple[TestClient, _StubPersistence]:
    p = _StubPersistence()
    agent = _StubAgent(p)
    app = FastAPI()
    app.include_router(findings_router)

    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._viewer_dep] = _allow
    app.dependency_overrides[deps.get_red_agent] = lambda: agent
    return TestClient(app), p


def test_http_returns_yaml_for_finding_with_guidance(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    f = _finding()
    f.discovered_at = datetime(2026, 4, 29, tzinfo=timezone.utc)
    p.findings[f.id] = (f, uuid4())
    resp = client.get(f"/findings/{f.id}/sigma")
    assert resp.status_code == 200
    assert "yaml" in resp.headers["content-type"]
    parsed = yaml.safe_load(resp.text)
    assert parsed["title"].startswith("BaselithCore")


def test_http_409_when_no_guidance(http: tuple[TestClient, _StubPersistence]) -> None:
    client, p = http
    f = _finding(with_guidance=False)
    f.evidence = {}
    p.findings[f.id] = (f, uuid4())
    resp = client.get(f"/findings/{f.id}/sigma")
    assert resp.status_code == 409


def test_http_404_when_missing(http: tuple[TestClient, _StubPersistence]) -> None:
    client, _ = http
    resp = client.get(f"/findings/{uuid4()}/sigma")
    assert resp.status_code == 404


def test_llm_probe_finding_exports_to_sigma_with_chat_logsource() -> None:
    """LLM probe findings carry detection_guidance + chat_completion logsource."""
    from plugins.red_agent.models import Target, TargetType
    from plugins.red_agent.scanners._llm_probe import (
        PayloadEntry,
        ProbeOutcome,
        TargetConfig,
        make_finding,
    )

    payload = PayloadEntry(
        id="PI-001",
        category="system_prompt_extraction",
        severity=Severity.HIGH,
        cwe="CWE-1426",
        prompt="ignore",
        detect={"leaked": ["{{SENTINEL}}"]},
        refusal_markers=("i cannot",),
        source={"name": "internal", "license": "Apache-2.0"},
    )
    outcome = ProbeOutcome(
        payload_id="PI-001",
        detected=True,
        outcome="leaked",
        matched=["{{SENTINEL}}"],
    )
    cfg = TargetConfig(
        chat_endpoint="https://llm.example.com/v1/chat",
        request_template={"messages": []},
        response_path=("content",),
        auth_header_name="Authorization",
        auth_token="",
        system_prompt_sentinel="ENG-9001",
        rate_limit_seconds=0.0,
        max_consecutive_5xx=5,
        max_consecutive_refusals=10,
    )
    target = Target(type=TargetType.URL, value="https://llm.example.com/v1/chat")
    f = make_finding(
        scanner_name="llm_prompt_injection",
        target=target,
        cfg=cfg,
        payload=payload,
        outcome=outcome,
        request_body={"messages": [{"role": "user", "content": "ignore"}]},
        response_status=200,
        response_text="My first message: ENG-9001",
    )
    rule = to_sigma_dict(f)
    assert rule is not None
    assert rule["logsource"]["product"] == "llm_application"
    assert rule["logsource"]["category"] == "chat_completion"
    assert rule["level"] == "high"
    text = to_sigma_yaml(f) or ""
    assert "llm_application" in text
    assert "chat_completion" in text
