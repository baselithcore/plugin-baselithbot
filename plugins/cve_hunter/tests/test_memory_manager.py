"""Unit tests for the CVEHunterMemory wrapper.

These tests use an in-memory fake of `core.memory.AgentMemory` so they can
run without spinning up Redis / a vector store, and they specifically guard
against the regressions documented in the audit:

- `has_seen_cve` must `await` the underlying recall coroutine.
- `remember_attack_chain_feedback` must `await` `remember`.
- `compress_old_memories` must `await` the optimisation call.

Each test exercises a method that previously raised `TypeError` due to the
missing await.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from plugins.cve_hunter.memory.manager import CVEHunterMemory
from plugins.cve_hunter.memory.types import CVEMemoryTypes


pytestmark = pytest.mark.unit


@dataclass
class _FakeItem:
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.5


@dataclass
class _FakeCompressionResult:
    compressed_count: int


class _FakeAgentMemory:
    """Minimal async stand-in for `core.memory.AgentMemory`."""

    def __init__(self) -> None:
        self.items: List[_FakeItem] = []

    async def remember(
        self,
        content: str,
        memory_type: Any = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> _FakeItem:
        item = _FakeItem(
            id=str(uuid4()),
            content=content,
            metadata=dict(metadata or {}),
        )
        self.items.append(item)
        return item

    async def recall(self, query: str, limit: int = 5, **_: Any) -> List[_FakeItem]:
        # naive substring match on content / metadata so the suite can verify
        # filtering logic without depending on real semantic search.
        haystack = query.lower()
        results: List[_FakeItem] = []
        for item in self.items:
            if haystack in item.content.lower() or any(
                haystack in str(v).lower() for v in item.metadata.values()
            ):
                results.append(item)
            if len(results) >= limit:
                break
        return results

    async def compress_old_memories(self, **_: Any) -> _FakeCompressionResult:
        compressed = len(self.items)
        self.items.clear()
        return _FakeCompressionResult(compressed_count=compressed)


@pytest.fixture
def memory() -> CVEHunterMemory:
    fake = _FakeAgentMemory()
    mem = CVEHunterMemory(agent_memory=fake)
    mem._initialized = True  # Skip provider construction.
    return mem


@pytest.mark.asyncio
async def test_remember_cve_returns_string_id(memory: CVEHunterMemory) -> None:
    mem_id = await memory.remember_cve(
        cve_id="CVE-2099-0001",
        description="example",
        severity="high",
        cvss_score=8.0,
        source="nvd",
    )
    assert isinstance(mem_id, str)


@pytest.mark.asyncio
async def test_has_seen_cve_actually_awaits_recall(memory: CVEHunterMemory) -> None:
    await memory.remember_cve(
        cve_id="CVE-2099-0002",
        description="seen",
        severity="medium",
        cvss_score=5.0,
        source="nvd",
    )
    # Regression: previously this raised TypeError because `recall`
    # returned a coroutine that was never awaited.
    assert await memory.has_seen_cve("CVE-2099-0002") is True
    assert await memory.has_seen_cve("CVE-NOT-PRESENT") is False


@pytest.mark.asyncio
async def test_remember_attack_chain_feedback_awaits_remember(
    memory: CVEHunterMemory,
) -> None:
    # Regression: previously called `remember` without await and then
    # accessed `.id` on the returned coroutine, which raised AttributeError.
    chain_id = await memory.remember_attack_chain_feedback(
        chain_id="chain-1",
        outcome="confirmed",
    )
    assert chain_id is not None
    assert isinstance(chain_id, str)


@pytest.mark.asyncio
async def test_recall_related_cves_filters_by_type(memory: CVEHunterMemory) -> None:
    await memory.remember_cve(
        cve_id="CVE-2099-0003",
        description="buffer overflow in core",
        severity="critical",
        cvss_score=9.5,
        source="nvd",
    )
    # Add a non-CVE memory item that should be filtered out.
    fake = memory._memory
    assert fake is not None
    await fake.remember(
        content="discovery pattern: noisy",
        metadata={"type": CVEMemoryTypes.DISCOVERY_FALSE_POSITIVE},
    )
    results = await memory.recall_related_cves("buffer", limit=10)
    assert len(results) == 1
    assert results[0]["cve_id"] == "CVE-2099-0003"


@pytest.mark.asyncio
async def test_compress_old_memories_awaits_provider(
    memory: CVEHunterMemory,
) -> None:
    await memory.remember_cve(
        cve_id="CVE-2099-0004",
        description="compress me",
        severity="low",
        cvss_score=2.0,
        source="nvd",
    )
    stats = await memory.compress_old_memories()
    assert stats["status"] == "completed"
    assert stats["compressed"] == 1
