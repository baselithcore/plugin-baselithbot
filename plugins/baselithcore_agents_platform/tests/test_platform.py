"""Unit tests for the Agents Platform.

All LLM access is mocked: tests assert orchestration, scope enforcement, and
documentation grounding without contacting a provider. The suite mirrors the
framework convention of mocking LLMs/DBs in unit tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plugins.baselithcore_agents_platform import builder as builder_mod
from plugins.baselithcore_agents_platform import runtime as runtime_mod
from plugins.baselithcore_agents_platform.builder import BlueprintBuilder
from plugins.baselithcore_agents_platform.docs_index import DocIndexer
from plugins.baselithcore_agents_platform.registry import AgentRegistry
from plugins.baselithcore_agents_platform.runtime import AgentRuntime
from plugins.baselithcore_agents_platform.types import (
    AgentBlueprint,
    AgentCapability,
    BlueprintScope,
    ModelProvider,
    RunStatus,
)


class _FakeLLM:
    """Minimal stand-in for ``LLMService`` returning a canned response."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def generate_response(self, **_: object) -> str:
        return self._response


@pytest.fixture
def docs(tmp_path: Path) -> DocIndexer:
    """A tiny two-document corpus for deterministic grounding tests."""
    (tmp_path / "GUIDE.md").write_text(
        "# Plugins\nPlugins must declare a manifest with integrity_sha256.\n",
        encoding="utf-8",
    )
    (tmp_path / "ARCH.md").write_text(
        "# Orchestration\nThe loop budget bounds iterations.\n",
        encoding="utf-8",
    )
    return DocIndexer(tmp_path, globs=("*.md",))


def _blueprint(**overrides: object) -> AgentBlueprint:
    base: dict[str, object] = {
        "id": "test-agent",
        "name": "Test Agent",
        "description": "does things",
        "provider": ModelProvider.OLLAMA,
        "scope": BlueprintScope(capabilities=[AgentCapability.GENERATE]),
    }
    base.update(overrides)
    return AgentBlueprint(**base)  # type: ignore[arg-type]


async def test_docs_index_search_ranks_relevant_section(docs: DocIndexer) -> None:
    hits = await docs.search("manifest integrity", top_k=2)
    assert hits, "expected at least one hit"
    assert hits[0].namespace == "GUIDE.md"


async def test_docs_namespace_filter(docs: DocIndexer) -> None:
    hits = await docs.search("loop budget", namespaces=["GUIDE.md"])
    assert hits == [], "namespace filter must exclude ARCH.md"


async def test_builder_parses_model_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps(
        {
            "name": "JSON Schema Agent",
            "description": "generates models",
            "provider": "anthropic",
            "scope": {"capabilities": ["generate", "refactor"], "language": "python"},
        }
    )
    monkeypatch.setattr(
        builder_mod, "resolve_llm_service", lambda *a, **k: _FakeLLM(payload)
    )
    bp = await BlueprintBuilder(ModelProvider.ANTHROPIC).build("make models")
    assert bp.provider is ModelProvider.ANTHROPIC
    assert set(bp.scope.capabilities) == {
        AgentCapability.GENERATE,
        AgentCapability.REFACTOR,
    }


async def test_builder_falls_back_on_bad_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        builder_mod, "resolve_llm_service", lambda *a, **k: _FakeLLM("not json")
    )
    bp = await BlueprintBuilder().build("an agent that does X")
    assert bp.scope.capabilities == [AgentCapability.GENERATE]
    assert bp.source_prompt == "an agent that does X"


async def test_runtime_rejects_out_of_scope_capability(docs: DocIndexer) -> None:
    runtime = AgentRuntime(docs)
    result = await runtime.run(_blueprint(), AgentCapability.FIX, "boom")
    assert result.status is RunStatus.REJECTED
    assert "outside" in (result.error or "")


async def test_runtime_generate_is_grounded(
    docs: DocIndexer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runtime_mod, "resolve_llm_service", lambda *a, **k: _FakeLLM("print('ok')")
    )
    runtime = AgentRuntime(docs)
    result = await runtime.run(
        _blueprint(), AgentCapability.GENERATE, "manifest integrity helper"
    )
    assert result.status is RunStatus.SUCCEEDED
    assert result.output == "print('ok')"
    assert any(c.namespace == "GUIDE.md" for c in result.citations)


async def test_runtime_strips_code_fences(
    docs: DocIndexer, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenced = "```python\nx = 1\n```"
    monkeypatch.setattr(
        runtime_mod, "resolve_llm_service", lambda *a, **k: _FakeLLM(fenced)
    )
    runtime = AgentRuntime(docs)
    result = await runtime.run(_blueprint(), AgentCapability.GENERATE, "set x")
    assert result.output == "x = 1"


async def test_runtime_test_capability_via_coding_agent_adapter(
    docs: DocIndexer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The injected adapter bridges LLMService.generate_response → CodingAgent.

    Regression guard: CodingAgent calls ``llm.generate(...).content`` but the
    framework LLMService exposes ``generate_response`` — without the adapter the
    test/fix path raises ``'LLMService' object has no attribute 'generate'``.
    """
    monkeypatch.setattr(
        runtime_mod,
        "resolve_llm_service",
        lambda *a, **k: _FakeLLM("def test_ok():\n    assert True"),
    )
    runtime = AgentRuntime(docs)
    bp = _blueprint(scope=BlueprintScope(capabilities=[AgentCapability.TEST]))
    result = await runtime.run(bp, AgentCapability.TEST, "def f(): return 1")
    assert result.status is RunStatus.SUCCEEDED
    assert "def test_ok" in result.output


async def test_runtime_records_loop_budget(
    docs: DocIndexer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runtime_mod, "resolve_llm_service", lambda *a, **k: _FakeLLM("print(1)")
    )
    runtime = AgentRuntime(docs)
    result = await runtime.run(_blueprint(), AgentCapability.GENERATE, "task")
    assert result.metadata["budget"] == {"iterations": 1, "tool_calls": 1}


async def test_mcp_tools_return_skillresult_envelope(
    docs: DocIndexer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from plugins.baselithcore_agents_platform.mcp_tools import build_platform_mcp_tools
    from plugins.baselithcore_agents_platform.service import AgentPlatformService

    monkeypatch.setattr(
        runtime_mod, "resolve_llm_service", lambda *a, **k: _FakeLLM("print(1)")
    )
    service = AgentPlatformService(repo_root=docs._repo_root)  # type: ignore[arg-type]
    tools = {t["name"]: t["handler"] for t in build_platform_mcp_tools(service)}

    env = await tools["search_baselith_docs"]("manifest", "", 2)
    assert env["success"] is True
    assert set(env) >= {"success", "message", "data", "snapshot", "error_code"}

    bad = await tools["run_agent"]("missing", "generate", "x")
    assert bad["success"] is False and bad["error_code"] == "not_found"


async def test_operate_runs_react_loop_with_tools(
    docs: DocIndexer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The operate capability drives a live ReAct loop over runtime tools."""
    from plugins.baselithcore_agents_platform import executor as executor_mod
    from plugins.baselithcore_agents_platform.executor import AgentExecutor
    from plugins.baselithcore_agents_platform.tools_runtime import ToolConfig

    class _ScriptedLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_response(self, **_: object) -> str:
            self.calls += 1
            if self.calls == 1:
                return "Thought: check the time\nAction: now()"
            return "Thought: done\nFinal Answer: completed"

    monkeypatch.setattr(
        executor_mod, "resolve_llm_service", lambda *a, **k: _ScriptedLLM()
    )
    executor = AgentExecutor(ToolConfig())
    runtime = AgentRuntime(docs, executor=executor)
    bp = _blueprint(
        scope=BlueprintScope(
            capabilities=[AgentCapability.OPERATE], allowed_tools=["now"]
        )
    )
    result = await runtime.run(bp, AgentCapability.OPERATE, "what time is it?")
    assert result.status is RunStatus.SUCCEEDED
    assert result.output == "completed"
    assert result.metadata["tools"] == ["now"]
    assert any("now()" in step for step in result.metadata["trace"])


async def test_http_get_blocks_redirect_to_private_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A redirect to a private/link-local host must be refused (SSRF guard)."""
    from plugins.baselithcore_agents_platform import tools_runtime as tools_mod
    from plugins.baselithcore_agents_platform.tools_runtime import (
        ToolConfig,
        build_runtime_tools,
    )

    # Public seed host resolves public; the redirect target is cloud-metadata.
    def fake_getaddrinfo(host: str, *_: object) -> list:
        ip = "1.2.3.4" if host == "example.com" else host
        return [(0, 0, 0, "", (ip, 0))]

    monkeypatch.setattr(tools_mod.socket, "getaddrinfo", fake_getaddrinfo)

    class _Resp:
        status_code = 302
        headers = {"location": "http://169.254.169.254/latest/meta-data/"}
        text = ""

    class _FakeClient:
        def __init__(self, **_: object) -> None: ...
        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def get(self, _url: str) -> _Resp:
            return _Resp()

    monkeypatch.setattr(tools_mod.httpx, "AsyncClient", _FakeClient)

    tools = build_runtime_tools(["http_get"], ToolConfig())
    http_get = tools[0].fn
    result = await http_get("http://example.com/")
    assert result.startswith("refused:")
    assert "169.254.169.254" in result or "blocked" in result


async def test_scheduler_add_list_remove() -> None:
    from plugins.baselithcore_agents_platform.scheduler import IntervalScheduler
    from plugins.baselithcore_agents_platform.types import ScheduleSpec

    async def _cb(_: ScheduleSpec) -> None:  # never fired in this test
        return None

    sched = IntervalScheduler(_cb)
    spec = ScheduleSpec(
        id="s1",
        blueprint_id="bp",
        capability=AgentCapability.OPERATE,
        task="ping",
        interval_seconds=8 * 3600,
    )
    sched.add(spec)
    assert [s.id for s in sched.list()] == ["s1"]
    assert sched.remove("s1") is True
    assert sched.remove("s1") is False


async def test_operate_out_of_scope_still_rejected(docs: DocIndexer) -> None:
    runtime = AgentRuntime(docs)
    bp = _blueprint(scope=BlueprintScope(capabilities=[AgentCapability.GENERATE]))
    result = await runtime.run(bp, AgentCapability.OPERATE, "do it")
    assert result.status is RunStatus.REJECTED


async def test_registry_roundtrip_and_run_history() -> None:
    registry = AgentRegistry(max_runs=2)
    bp = _blueprint()
    await registry.save_blueprint(bp)
    assert (await registry.get_blueprint("test-agent")) is not None
    assert [b.id for b in await registry.list_blueprints()] == ["test-agent"]
    assert await registry.delete_blueprint("test-agent") is True
    assert await registry.delete_blueprint("test-agent") is False
