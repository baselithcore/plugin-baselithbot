"""Handler loading and management mixin for HoneypotSwarmCoordinator.

Handles dynamic handler loading and parallel startup of honeypot listeners.
"""

import asyncio
from core.observability.logging import get_logger
from typing import TYPE_CHECKING, Optional

from ..engine.base import BaseHandler
from ..engine.ssh_handler import ASYNCSSH_AVAILABLE

if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)


class HandlerMixin:
    """Mixin providing handler loading and management capabilities."""

    def _load_custom_handler(
        self: "HoneypotSwarmCoordinator", class_path: str
    ) -> Optional[type]:
        """Dynamically load a custom handler class.

        Args:
            class_path: Dot-separated path to class (e.g. 'my.module.MyClass')

        Returns:
            The handler class or None if not found/invalid.
        """
        import importlib

        try:
            module_name, class_name = class_path.rsplit(".", 1)
            # Try importing from custom_handlers first if not absolute
            if not module_name.startswith("plugins.honeypot"):
                try:
                    module = importlib.import_module(
                        f"plugins.honeypot.custom_handlers.{module_name}"
                    )
                except ImportError:
                    module = importlib.import_module(module_name)
            else:
                module = importlib.import_module(module_name)

            handler_class = getattr(module, class_name)
            if not issubclass(handler_class, BaseHandler):
                raise TypeError(f"{class_path} must inherit from BaseHandler")

            return handler_class
        except Exception as e:
            logger.error(f"Error loading custom handler {class_path}: {e}")
            return None

    async def _start_dynamic_listeners(self: "HoneypotSwarmCoordinator") -> None:
        """Start network listeners for dynamically loaded honeypots."""
        from ..engine.http_handler import HTTPHandler
        from ..engine.ssh_handler import SSHHandler
        from ..engine.tcp_handler import TCPHandler

        handlers_to_start = []

        for definition in self._registry.list_all():
            if not definition.enabled:
                continue

            # Skip if already running
            if definition.id in self._handlers_by_honeypot:
                continue

            # Determine handler type
            handler: Optional[BaseHandler] = None
            try:
                # Prioritize Custom Handlers
                if (
                    definition.handler_type == "custom"
                    and definition.custom_handler_class
                ):
                    try:
                        handler_class = self._load_custom_handler(
                            definition.custom_handler_class
                        )
                        if handler_class:
                            handler = handler_class(self.config, definition=definition)
                    except Exception as e:
                        logger.error(
                            f"Failed to load custom handler "
                            f"'{definition.custom_handler_class}' "
                            f"for honeypot '{definition.name}': {e}"
                        )
                        continue

                # Cloud Management Handler (high-interaction)
                elif definition.handler_type == "cloud":
                    from ..engine.cloud import CloudManagementHandler

                    handler = CloudManagementHandler(
                        self.config,
                        definition=definition,
                    )

                # Standard Protocol Handlers
                elif definition.protocol == "ssh":
                    if ASYNCSSH_AVAILABLE:
                        handler = SSHHandler(self.config, definition=definition)
                    else:
                        logger.warning(
                            f"Skipping SSH honeypot '{definition.name}': "
                            "asyncssh not available"
                        )
                        continue
                elif definition.protocol == "http":
                    handler = HTTPHandler(self.config, definition=definition)
                elif definition.protocol == "tcp":
                    handler = TCPHandler(self.config, definition=definition)

                # IoT/OT Protocol Handlers
                elif definition.protocol in ("modbus", "mqtt", "s7comm"):
                    from ..engine.iot import get_iot_handler

                    handler = get_iot_handler(
                        definition.protocol,
                        self.config,
                        definition,
                    )
                    if not handler:
                        logger.warning(
                            f"Skipping IoT honeypot '{definition.name}': "
                            f"unsupported protocol '{definition.protocol}'"
                        )
                        continue

                if handler:
                    # Bind event callback with captured honeypot_id
                    handler.set_event_callback(
                        lambda event, hid=definition.id: (
                            self._process_attack_with_honeypot(event, hid)
                        )
                    )

                    # HoneyDOC: set flow check callback
                    handler.set_flow_check_callback(self._check_flow_allowed)

                    self._handlers_by_honeypot[definition.id] = handler
                    handlers_to_start.append((definition, handler))

            except Exception as e:
                logger.error(
                    f"Error initializing dynamic honeypot '{definition.name}': {e}"
                )

        # Start all collected handlers in parallel
        if handlers_to_start:
            logger.info(f"Starting {len(handlers_to_start)} honeypots in parallel...")

            async def start_handler(defn, hlr):
                try:
                    await hlr.start(port=defn.port)
                    logger.info(
                        f"Started dynamic honeypot '{defn.name}' "
                        f"({defn.id}) on port {defn.port}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to start dynamic honeypot '{defn.name}' "
                        f"on port {defn.port}: {e}"
                    )
                    # Remove from running handlers if start failed
                    self._handlers_by_honeypot.pop(defn.id, None)

            await asyncio.gather(*(start_handler(d, h) for d, h in handlers_to_start))
