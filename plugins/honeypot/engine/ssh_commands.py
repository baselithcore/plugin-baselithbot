"""SSH Command Handler with Virtual Filesystem.

DEPRECATED: This module has been refactored into the commands/ package.
This file is kept for backward compatibility only.

New code should import from:
    from plugins.honeypot.engine.commands import CommandProcessor, generate_command_response
"""

# Re-export from new modular structure for backward compatibility
from .commands import (
    CommandProcessor,
    generate_command_response,
    SHELL_BUILTINS,
)

__all__ = [
    "CommandProcessor",
    "generate_command_response",
    "SHELL_BUILTINS",
]
