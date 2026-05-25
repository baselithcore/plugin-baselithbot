"""Sandbox provider implementations for the Red Agent.

The legacy Docker-backed provider stays at the package root in
``plugins.red_agent.sandbox_runner.SandboxRunner`` for backwards
compatibility; the alternative providers documented here are imported
lazily via ``select_sandbox_provider``.
"""

from __future__ import annotations

from plugins.red_agent.sandbox.protocol import SandboxProtocol

__all__ = ["SandboxProtocol"]
