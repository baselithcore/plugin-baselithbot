"""Governed lifecycle operations: RBAC + autonomy + audit, then delegate to core.

Lifecycle mutation is the only privileged path in the plugin. It applies three
gates, fail-closed:

1. ``require_roles(ADMIN)`` at the route layer (see ``router/actions.py``).
2. An optional :class:`AutonomyPolicy` approval for destructive/mutating ops —
   off by default (RBAC is the gate); tightened per environment via config.
3. An append-only audit record for every attempt, allowed or denied.

The actual state change reuses the registry the core already exposes — no
duplicate lifecycle logic lives here.
"""

from __future__ import annotations

import asyncio
from typing import Any

from core.observability.logging import get_logger
from core.orchestration.autonomy import (
    DESTRUCTIVE,
    MUTATING,
    ApprovalRequiredError,
    AutonomyPolicy,
    enforce_approval,
)

from ..api_models import ActionResult, PluginState
from .audit import AuditSink
from .bridge import emit_action
from .config_store import read_block, set_enabled
from .manifests import read_manifest

logger = get_logger(__name__)

_VALID_OPS = ("enable", "disable", "reload")
# Map each op onto an autonomy tool category (consulted only when gating is on).
_OP_CATEGORY = {"disable": DESTRUCTIVE, "reload": MUTATING, "enable": MUTATING}


class ControlService:
    """Apply gated lifecycle operations against the live plugin registry."""

    def __init__(
        self,
        registry: Any,
        *,
        policy: AutonomyPolicy,
        audit: AuditSink,
        human_intervention: Any | None = None,
        approval_timeout: int = 60,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._audit = audit
        self._human = human_intervention
        self._timeout = approval_timeout

    async def run(
        self, *, plugin: str, op: str, actor: str, reason: str | None
    ) -> ActionResult:
        """Validate, gate, execute, and audit a single lifecycle operation."""
        if op not in _VALID_OPS:
            return ActionResult(
                plugin=plugin,
                operation=op,
                ok=False,
                state=PluginState.unknown,
                message="unsupported",
            )
        if plugin not in self._registry:
            return ActionResult(
                plugin=plugin,
                operation=op,
                ok=False,
                state=PluginState.unknown,
                message="not_found",
            )

        try:
            await enforce_approval(
                self._policy,
                _OP_CATEGORY[op],
                f"{op}:{plugin}",
                human_intervention=self._human,
                timeout=self._timeout,
            )
        except ApprovalRequiredError as exc:
            await self._audit.record(
                actor=actor, plugin=plugin, op=op, ok=False, reason=str(exc)
            )
            return ActionResult(
                plugin=plugin,
                operation=op,
                ok=False,
                state=PluginState.active,
                message=f"denied: {exc.reason}",
            )

        ok, state = await self._dispatch(plugin, op)
        await self._audit.record(
            actor=actor, plugin=plugin, op=op, ok=ok, reason=reason
        )
        await emit_action(plugin=plugin, op=op, ok=ok, state=state.value)
        return ActionResult(
            plugin=plugin,
            operation=op,
            ok=ok,
            state=state,
            message="ok" if ok else "failed",
        )

    async def set_config_enabled(
        self, *, plugin: str, enabled: bool, actor: str, reason: str | None
    ) -> ActionResult:
        """Persist the plugin's ``enabled`` flag in plugins.yaml + sync runtime.

        Writes the config (durable across restarts), then best-effort applies the
        change to the live registry so the dashboard reflects it immediately.
        Admin-gated at the route; audited here.
        """
        op = "config_enable" if enabled else "config_disable"
        # A config-disabled plugin is absent from the live registry by design —
        # the loader skips it at boot. Enabling it must therefore NOT require
        # registry membership; we only reject a plugin that exists nowhere
        # (neither loaded nor installed on disk).
        installed = bool(await asyncio.to_thread(read_manifest, plugin))
        if plugin not in self._registry and not installed:
            return ActionResult(
                plugin=plugin,
                operation=op,
                ok=False,
                state=PluginState.unknown,
                message="not_found",
            )

        wrote = await asyncio.to_thread(set_enabled, plugin, enabled)
        if not wrote:
            await self._audit.record(
                actor=actor,
                plugin=plugin,
                op=op,
                ok=False,
                reason="config write failed",
            )
            return ActionResult(
                plugin=plugin,
                operation=op,
                ok=False,
                state=PluginState.unknown,
                message="config_write_failed",
            )

        # Best-effort runtime sync so the UI updates without a restart.
        _, state = await self._dispatch(plugin, "enable" if enabled else "disable")
        await self._audit.record(
            actor=actor, plugin=plugin, op=op, ok=True, reason=reason
        )
        await emit_action(plugin=plugin, op=op, ok=True, state=state.value)
        return ActionResult(
            plugin=plugin, operation=op, ok=True, state=state, message="ok"
        )

    @staticmethod
    def _controller() -> Any | None:
        """Return the core hot-reload controller, or ``None`` if unavailable.

        The controller is the only lifecycle primitive that can load a *disabled*
        plugin from disk on demand (``ensure_plugin_active`` only activates
        already-discovered ones, and the loader skips disabled plugins at boot).
        Routing every op through it also keeps the core lifecycle state machine
        consistent, so a disable→enable round-trip re-registers cleanly.
        """
        try:
            from core.plugins.api import get_controller

            return get_controller()
        except Exception:  # noqa: BLE001 — controller optional; fall back to registry
            return None

    async def _dispatch(self, plugin: str, op: str) -> tuple[bool, PluginState]:
        """Delegate to the core lifecycle controller (registry as fallback)."""
        controller = self._controller()
        try:
            if op == "reload":
                if controller is not None:
                    config = await asyncio.to_thread(read_block, plugin)
                    ok = bool(await controller.reload_plugin(plugin, config))
                else:
                    ok = bool(await self._registry.reload_plugin(plugin))
                return ok, PluginState.active if ok else PluginState.failed
            if op == "disable":
                if controller is not None:
                    ok = bool(await controller.disable_plugin(plugin))
                else:
                    await self._registry.unregister(plugin)
                    ok = True
                return ok, PluginState.disabled if ok else PluginState.active
            if op == "enable":
                if controller is not None:
                    config = await asyncio.to_thread(read_block, plugin)
                    ok = bool(await controller.enable_plugin(plugin, config))
                else:
                    ok = bool(await self._registry.ensure_plugin_active(plugin))
                return ok, PluginState.active if ok else PluginState.failed
        except Exception as exc:  # noqa: BLE001 — surface failure, never crash route
            logger.warning("lifecycle op '%s' on '%s' failed: %s", op, plugin, exc)
            return False, PluginState.failed
        return False, PluginState.unknown


__all__ = ["ControlService"]
