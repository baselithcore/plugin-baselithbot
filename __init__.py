"""dbview plugin — database visualisation + NL→Query workbench (18 engines).

Hosts the vendored dbview TypeScript stack (NestJS API + React SPA under
``dbview/``) as a supervised Node child process behind an authenticated
FastAPI reverse proxy. Identity, RBAC and tenancy are centralised in the
platform ``auth`` plugin; see :mod:`plugins.dbview.plugin` for the contract.
"""

from .plugin import DbviewPlugin

__all__ = ["DbviewPlugin"]
