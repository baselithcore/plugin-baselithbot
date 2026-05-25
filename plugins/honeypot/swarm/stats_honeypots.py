"""Honeypot registry query methods for HoneypotSwarmCoordinator.

Handles retrieval of registered honeypots with statistics.
"""

from typing import TYPE_CHECKING, List, Optional

from ..models import HoneypotInfo

if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator


class HoneypotRegistryMixin:
    """Mixin providing honeypot registry query capabilities."""

    async def get_honeypots(self: "HoneypotSwarmCoordinator") -> List[HoneypotInfo]:
        """Get list of all registered honeypots with stats from database.

        Uses database queries to get accurate stats that persist across restarts.
        """
        from ..persistence import HoneypotDAO

        honeypots: List[HoneypotInfo] = []

        # Helper to get DB stats for a honeypot
        async def get_hp_stats(honeypot_id: str) -> tuple[int, int]:
            """Get (active_attackers, total_events) from DB."""
            try:
                stats = await HoneypotDAO.get_stats(honeypot_id=honeypot_id, days=365)
                return (stats.get("unique_ips", 0), stats.get("total_events", 0))
            except Exception:
                return (0, 0)

        # Add legacy honeypots from config (for backwards compatibility)
        allow_legacy_http = True
        if self.config.enforce_active_honeypots_only:
            allow_legacy_http = (
                "legacy-http" in self.config.active_honeypots
                and self.config.active_honeypots["legacy-http"].get("enabled", False)
            )

        if self.config.enable_http_honeypot and allow_legacy_http:
            active_attackers, total_events = await get_hp_stats("legacy-http")
            honeypots.append(
                HoneypotInfo(
                    id="legacy-http",
                    name="HTTP Honeypot (Legacy)",
                    description="HTTP honeypot from plugins.yaml config",
                    protocol="http",
                    port=self.config.http_port,
                    enabled=True,
                    active_attackers=active_attackers,
                    total_events=total_events,
                    tags=["legacy", "http"],
                )
            )

        # Check if legacy-ssh is allowed
        allow_legacy_ssh = True
        if self.config.enforce_active_honeypots_only:
            allow_legacy_ssh = (
                "legacy-ssh" in self.config.active_honeypots
                and self.config.active_honeypots["legacy-ssh"].get("enabled", False)
            )

        if self.config.enable_ssh_honeypot and allow_legacy_ssh:
            active_attackers, total_events = await get_hp_stats("legacy-ssh")
            honeypots.append(
                HoneypotInfo(
                    id="legacy-ssh",
                    name="SSH Honeypot (Legacy)",
                    description="SSH honeypot from plugins.yaml config",
                    protocol="ssh",
                    port=self.config.ssh_port,
                    enabled=True,
                    active_attackers=active_attackers,
                    total_events=total_events,
                    tags=["legacy", "ssh"],
                )
            )

        # Add YAML-defined honeypots
        if self._registry:
            for definition in self._registry.list_all():
                if not definition.enabled:
                    continue

                active_attackers, total_events = await get_hp_stats(definition.id)

                honeypots.append(
                    HoneypotInfo(
                        id=definition.id,
                        name=definition.name,
                        description=definition.description,
                        protocol=definition.protocol.value,
                        port=definition.port,
                        enabled=definition.enabled,
                        active_attackers=active_attackers,
                        total_events=total_events,
                        tags=definition.tags,
                    )
                )

        return honeypots

    async def get_honeypot(
        self: "HoneypotSwarmCoordinator", honeypot_id: str
    ) -> Optional[HoneypotInfo]:
        """Get specific honeypot by ID with stats from database."""
        honeypots = await self.get_honeypots()
        for hp in honeypots:
            if hp.id == honeypot_id:
                return hp
        return None


__all__ = ["HoneypotRegistryMixin"]
