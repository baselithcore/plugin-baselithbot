"""Tenant context propagation tests."""

import asyncio

from docheck.core.tenant import (
    current_tenant,
    reset_tenant,
    resolve_tenant_from_request,
    set_tenant,
)


def test_default_tenant_is_default() -> None:
    assert current_tenant() == "default"


def test_set_and_reset() -> None:
    token = set_tenant("acme")
    assert current_tenant() == "acme"
    reset_tenant(token)
    assert current_tenant() == "default"


async def test_concurrent_tasks_isolated() -> None:
    """Each task carries its own tenant via ContextVar — no cross-leak."""
    seen: dict[str, str] = {}

    async def worker(name: str) -> None:
        token = set_tenant(name)
        await asyncio.sleep(0)  # yield to scheduler
        seen[name] = current_tenant()
        reset_tenant(token)

    await asyncio.gather(worker("acme"), worker("globex"), worker("initech"))
    assert seen == {"acme": "acme", "globex": "globex", "initech": "initech"}


def test_resolution_priority(monkeypatch) -> None:
    monkeypatch.setenv("DOCHECK_MULTITENANT_ENABLED", "true")
    import importlib

    from docheck.core import config

    importlib.reload(config)

    # JWT claim wins
    assert resolve_tenant_from_request({"x-tenant-id": "header-t"}, jwt_claims={"tid": "jwt-t"}) == "jwt-t"

    # Header fallback
    assert resolve_tenant_from_request({"x-tenant-id": "header-t"}, jwt_claims=None) == "header-t"

    # Default fallback
    assert resolve_tenant_from_request({}, jwt_claims=None) == "default"


def test_disabled_multitenant_always_default(monkeypatch) -> None:
    monkeypatch.setenv("DOCHECK_MULTITENANT_ENABLED", "false")
    import importlib

    from docheck.core import config

    importlib.reload(config)

    assert resolve_tenant_from_request({"x-tenant-id": "ignored"}, jwt_claims={"tid": "ignored"}) == "default"
