"""Public-API routers grouped by concern.

Each module exposes a ``router`` :class:`fastapi.APIRouter`. The
top-level FastAPI app in :mod:`main` mounts them via
``app.include_router``. Splitting keeps :mod:`main` to a thin app
factory (lifespan + middleware) instead of a 800-line monolith.
"""
