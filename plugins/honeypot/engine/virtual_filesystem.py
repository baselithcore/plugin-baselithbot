"""Virtual Filesystem for SSH Honeypot.

DEPRECATED: This module has been refactored into the vfs/ package.
This file is kept for backward compatibility only.

New code should import from:
    from plugins.honeypot.engine.vfs import VirtualFile, VirtualFilesystem
"""

from .vfs import VirtualFile, VirtualFilesystem

__all__ = ["VirtualFile", "VirtualFilesystem"]
