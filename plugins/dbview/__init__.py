"""dbview — TypeScript NestJS + React workbench hosted as a BaselithCore plugin.

The directory layout mirrors the wikigen / docheck plugin pattern:

* ``manifest.yaml`` — declarative metadata + dependency surface.
* ``plugin.py`` — :class:`DbviewPlugin` entry point (RouterPlugin).
* ``supervisor.py`` — async Node child-process lifecycle.
* ``proxy_router.py`` — reverse-proxy ``APIRouter`` mounted at ``/api/dbview``.
* ``dbview/`` — the upstream monorepo, byte-identical to the source repo
  modulo three documented env-driven UI patches (see ``plugin.py`` header).
"""

from .plugin import DbviewPlugin

__all__ = ["DbviewPlugin"]
