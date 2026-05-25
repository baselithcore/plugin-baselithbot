"""Virtual Filesystem implementation modules.

This package contains the modularized virtual filesystem for SSH honeypot.
"""

from .models import VirtualFile
from .core import VirtualFilesystem

__all__ = [
    "VirtualFile",
    "VirtualFilesystem",
]
