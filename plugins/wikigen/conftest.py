"""Plugin-root conftest — anchors sys.path so wikigen tests resolve `llm_wiki`.

When pytest is invoked from the BaselithCore repository root (not the
legacy wikigen repo root), the nested ``plugins/wikigen/llm_wiki/``
package is not on ``sys.path``. The plugin's runtime entry point fixes
this via ``plugin.py``'s ``sys.path`` bootstrap, but the test collector
runs before that module loads — so add the same bootstrap here.

Idempotent: a duplicate insertion is a no-op.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))
