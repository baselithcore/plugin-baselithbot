"""Static binary / file analysis scanner.

Reverse-engineers an uploaded sample without executing it. Produces
findings for: high-entropy (packed) sections, embedded IOCs (IPs, URLs,
domains, JWT, AWS keys, BTC wallets, registry keys, mutex names),
suspicious Win32 imports, missing Authenticode signature, embedded
private keys, and (when ``yara-python`` is available) custom YARA hits.

The scanner never spawns a child process for the sample — every parser
runs in-process on the bytes already quarantined under
``runtime/quarantine/<sha256>/``. The path is read from
``Target.metadata['path']`` set by ``routers/file_scan.py``.

Format coverage by default (pure stdlib):
  • PE / EXE / DLL / SYS / OCX
  • ELF (Linux .so, .out)
  • Mach-O (single-arch and FAT)
  • PDF, OLE/Office, ZIP/JAR/APK (entropy + IOC scan only)

Optional dependencies improve detail without changing the contract:
  • ``lief``       — rich PE/ELF parsing (signatures, TLS, .NET)
  • ``yara-python``— custom rule packs (rules dir env: ``RED_AGENT_YARA_RULES``)

This package re-exports the same public surface previously exposed by
the ``binary_analyzer`` module so existing import paths keep working.
"""

from __future__ import annotations

from plugins.red_agent.scanners.binary_analyzer._helpers import (
    _HIGH_ENTROPY_THRESHOLD,
    _MAX_BYTES,
)
from plugins.red_agent.scanners.binary_analyzer._scanner import BinaryAnalyzerScanner

__all__ = [
    "BinaryAnalyzerScanner",
]

# Preserve the module-level constants previously exposed at top level.
_ = (_MAX_BYTES, _HIGH_ENTROPY_THRESHOLD)
