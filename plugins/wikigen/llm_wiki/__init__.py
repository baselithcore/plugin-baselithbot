"""White-label LLM Wiki engine.

Core is **domain-agnostic** by contract: zero hardcoded prompts, page types,
or frontmatter assumptions. Everything domain-specific lives under
``domains/<APP_DOMAIN>/`` and is loaded at import time via
:func:`core.domain.registry.load_pack`.

Three boundaries you must never cross:

1. ``core/`` reads from ``domains/<APP_DOMAIN>/``, never the inverse.
2. Prompts live as Jinja2 templates inside the active Domain Pack.
3. All filesystem paths derive from :mod:`core.config` (``WIKI_ROOT``,
   ``DOMAIN_PACK_DIR``). No relative paths sprinkled across modules.
"""

from __future__ import annotations

__version__ = "0.1.0"
