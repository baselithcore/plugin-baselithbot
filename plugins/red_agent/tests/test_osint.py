"""OSINT scanner + ingestion unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from plugins.red_agent.integrations.easm import (
    DiscoveredAsset,
    EASMConnector,
    NoneEASMConnector,
    get_easm_connector,
    register_easm_connector,
)
from plugins.red_agent.integrations.osint_ingestion import (
    findings_to_assets,
    merge_external,
    select_for_promotion,
)
from plugins.red_agent.models import Finding, Severity, Target, TargetType
from plugins.red_agent.scanners.crtsh import CrtShScanner
from plugins.red_agent.scanners.subfinder import SubfinderScanner


def _target(value: str = "example.com") -> Target:
    return Target(type=TargetType.HOSTNAME, value=value)


def test_subfinder_parses_jsonl_dedups_and_drops_apex() -> None:
    sc = SubfinderScanner.__new__(SubfinderScanner)  # bypass sandbox dependency
    stdout = "\n".join(
        [
            '{"host":"api.example.com","source":"crt"}',
            '{"host":"api.example.com","source":"alienvault"}',  # dup
            '{"host":"dev.example.com","source":"chaos"}',
            '{"host":"example.com","source":"crt"}',  # apex itself: drop
            "not-json",
            "",
        ]
    )

    findings = sc._parse(stdout, _target())  # type: ignore[attr-defined]

    hosts = sorted(f.endpoint for f in findings if f.endpoint)
    assert hosts == ["api.example.com", "dev.example.com"]
    assert all(f.severity == Severity.INFO for f in findings)
    assert all(f.target == "example.com" for f in findings)


def test_crtsh_parses_payload_and_filters_by_apex() -> None:
    sc = CrtShScanner.__new__(CrtShScanner)
    payload: list[dict[str, Any]] = [
        {"name_value": "api.example.com\n*.api.example.com", "issuer_ca_id": 1},
        {"name_value": "evil.org", "issuer_ca_id": 2},
        {"name_value": "example.com", "issuer_ca_id": 3},  # apex: drop
        {"name_value": "dev.example.com", "issuer_ca_id": 4},
    ]

    findings = sc._parse(payload, _target())  # type: ignore[attr-defined]

    hosts = sorted(f.endpoint for f in findings if f.endpoint)
    assert hosts == ["api.example.com", "dev.example.com"]


def test_findings_to_assets_only_keeps_osint_scanners() -> None:
    findings = [
        Finding(
            scanner="subfinder",
            title="t",
            description="",
            severity=Severity.INFO,
            target="example.com",
            endpoint="api.example.com",
        ),
        Finding(
            scanner="nuclei",
            title="t",
            description="",
            severity=Severity.HIGH,
            target="example.com",
            endpoint="api.example.com",
        ),
    ]

    assets = findings_to_assets(findings, apex="example.com")

    assert len(assets) == 1
    assert assets[0].source == "subfinder"
    assert assets[0].host == "api.example.com"


@pytest.mark.asyncio
async def test_merge_external_appends_unique_connector_assets() -> None:
    builtin = [
        DiscoveredAsset(
            host="api.example.com",
            source="subfinder",
            discovered_at=datetime.now(timezone.utc),
        )
    ]

    class _Stub(EASMConnector):
        name = "stub_easm"

        async def discover(self, *, apex: str) -> list[DiscoveredAsset]:
            return [
                DiscoveredAsset(
                    host="api.example.com",
                    source="stub_easm",
                    discovered_at=datetime.now(timezone.utc),
                ),
                DiscoveredAsset(
                    host="legacy.example.com",
                    source="stub_easm",
                    discovered_at=datetime.now(timezone.utc),
                ),
            ]

    merged = await merge_external(
        connector=_Stub(), apex="example.com", builtin=builtin
    )

    sources = sorted({(a.host, a.source) for a in merged})
    assert sources == [
        ("api.example.com", "stub_easm"),
        ("api.example.com", "subfinder"),
        ("legacy.example.com", "stub_easm"),
    ]


@pytest.mark.asyncio
async def test_merge_external_fail_open_on_connector_exception() -> None:
    class _Boom(EASMConnector):
        name = "boom"

        async def discover(self, *, apex: str) -> list[DiscoveredAsset]:
            raise RuntimeError("upstream down")

    merged = await merge_external(connector=_Boom(), apex="example.com", builtin=[])

    assert merged == []


def _asset(host: str, source: str = "subfinder") -> DiscoveredAsset:
    return DiscoveredAsset(
        host=host, source=source, discovered_at=datetime.now(timezone.utc)
    )


def test_select_for_promotion_skips_known_and_out_of_scope() -> None:
    assets = [_asset("a.example.com"), _asset("b.example.com"), _asset("evil.org")]
    in_scope = lambda h: h.endswith(".example.com")  # noqa: E731

    result = select_for_promotion(
        assets,
        auto_promote=True,
        in_scope=in_scope,
        known_hosts={"b.example.com"},
        max_results=10,
    )

    assert [a.host for a in result.promoted] == ["a.example.com"]
    assert result.skipped_already_known == ["b.example.com"]
    assert result.skipped_out_of_scope == ["evil.org"]


def test_select_for_promotion_respects_auto_promote_off() -> None:
    result = select_for_promotion(
        [_asset("a.example.com")],
        auto_promote=False,
        in_scope=lambda _h: True,
        known_hosts=set(),
        max_results=10,
    )

    assert result.promoted == []


def test_select_for_promotion_caps_at_max_results() -> None:
    assets = [_asset(f"h{i}.example.com") for i in range(10)]

    result = select_for_promotion(
        assets,
        auto_promote=True,
        in_scope=lambda _h: True,
        known_hosts=set(),
        max_results=3,
    )

    assert len(result.promoted) == 3


def test_easm_connector_registry_default_and_override() -> None:
    assert isinstance(get_easm_connector(None), NoneEASMConnector)
    assert isinstance(get_easm_connector("none"), NoneEASMConnector)
    assert isinstance(get_easm_connector("does-not-exist"), NoneEASMConnector)

    class _Fake(EASMConnector):
        name = "fake"

        async def discover(self, *, apex: str) -> list[DiscoveredAsset]:
            return []

    register_easm_connector("fake", _Fake)
    try:
        assert isinstance(get_easm_connector("fake"), _Fake)
    finally:
        register_easm_connector("fake", NoneEASMConnector)
