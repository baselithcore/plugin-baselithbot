"""The Node child's LLM usage reaches the host's token-report seam.

dbview's NL→Query engine runs in a child process, so the host cannot observe the
tokens it spends: the per-plugin cost ledger behind the BaselithControl plugin
card showed dbview as having spent zero no matter how much was translated. The
child now reports what its providers measured on every response
(``x-dbview-llm-usage``) and the proxy — still inside the caller's request, so
the plugin and the user are attributable — forwards it to the framework seam.
"""

from __future__ import annotations

import pytest

from core.services.llm import register_token_sink, unregister_token_sink
from plugins.dbview.usage import USAGE_HEADER, parse_usage, report_upstream_usage


@pytest.fixture
def reports():
    seen: list[tuple[int, str]] = []

    def sink(count: int, model: str) -> None:
        seen.append((count, model))

    register_token_sink(sink)
    try:
        yield seen
    finally:
        unregister_token_sink(sink)


class TestParseUsage:
    def test_parses_one_row(self):
        assert parse_usage("codellama:7b;1200;80") == [("codellama:7b", 1200, 80)]

    def test_parses_several_rows(self):
        value = "codellama:7b;1200;80,gpt-4o-mini;10;4"
        assert parse_usage(value) == [
            ("codellama:7b", 1200, 80),
            ("gpt-4o-mini", 10, 4),
        ]

    @pytest.mark.parametrize(
        "value",
        ["", "   ", "nonsense", "model;abc;1", "model;1", "model;-5;-5", ";1;1"],
    )
    def test_rejects_garbage(self, value):
        # The header crosses a process boundary: a malformed value must be
        # dropped, never raise inside the proxy path.
        assert parse_usage(value) == []

    def test_caps_the_row_count(self):
        value = ",".join(f"m{i};1;1" for i in range(100))
        assert len(parse_usage(value)) == 32


class TestReportUpstreamUsage:
    def test_reports_each_row_paired(self, reports):
        report_upstream_usage({USAGE_HEADER: "codellama:7b;1200;80"})

        assert reports == [(1200, "input"), (80, "codellama:7b")]

    def test_no_header_reports_nothing(self, reports):
        report_upstream_usage({"content-type": "application/json"})

        assert reports == []

    def test_malformed_header_reports_nothing(self, reports):
        report_upstream_usage({USAGE_HEADER: "not-a-usage-row"})

        assert reports == []
