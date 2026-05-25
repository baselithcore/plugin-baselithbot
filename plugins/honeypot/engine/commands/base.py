"""Base class for command implementations."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..virtual_filesystem import VirtualFilesystem


class CommandMixin:
    """Base mixin for command implementations.

    Provides access to VirtualFilesystem and fingerprint data.
    """

    def __init__(self, vfs: "VirtualFilesystem", fingerprint: dict):
        """Initialize command mixin.

        Args:
            vfs: Virtual filesystem instance
            fingerprint: Honeypot fingerprint data
        """
        self.vfs = vfs
        self.fingerprint = fingerprint


# Alias for backward compatibility since other modules import BaseCommands
BaseCommands = CommandMixin
