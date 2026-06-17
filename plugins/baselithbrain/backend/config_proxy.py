"""Re-export the plugin's root :mod:`config` settings into the backend package.

The settings module lives at the plugin root (``plugins/baselithbrain/config.py``)
so it is reachable both by the host wrapper and the backend. A relative import
(``from ..config``) keeps resolution inside the plugin package namespace,
avoiding any collision with a top-level ``config`` module on ``sys.path``.
"""

from __future__ import annotations

from ..config import BrainSettings, get_settings

__all__ = ["BrainSettings", "get_settings"]
