"""Sandbox provider protocol.

Each provider (docker / k8s / mock) implements the same async
``execute`` signature so the orchestrator can swap backends without
touching scanner adapters. The protocol is structural (``runtime_checkable``)
and intentionally narrow: every scanner adapter goes through the same
input/output shape, eliminating any "docker-isms" from leaking into the
scanner code.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from plugins.red_agent.sandbox_runner import SandboxResult


@runtime_checkable
class SandboxProtocol(Protocol):
    """Minimal contract every sandbox provider must satisfy."""

    async def execute(
        self,
        *,
        image: str,
        argv: list[str],
        timeout: int,
        network: bool,
        scanner: str,
        artifacts: list[str] | None = None,
    ) -> SandboxResult: ...
