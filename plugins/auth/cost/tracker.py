"""Per-user LLM spend metering + monthly-cap enforcement.

The core runtime funnels every token count through one module-level sink,
``core.services.llm.service._report_tokens_to_middleware(count, model)`` (input
reported with ``model="input"``/``"input_stream"``, output with the real model).
We wrap that sink at runtime — no core edit, so the Sacred-Core boundary and the
architecture gate stay intact; the wrapper composes with any other (e.g. the
baselithcontrol per-plugin tracker), always calling through.

For each completed call we attribute spend to the **authenticated user**
(``core.context.get_current_user_id`` — identity-derived, bound at the auth
chokepoint; ``None`` for background/unauthenticated calls → skipped) and persist
it to the monthly ledger. Before a call we **enforce** the user's effective
monthly cap: once spend ≥ cap (and the policy enforces) the input report raises
``BudgetExceededError``, which the LLM service already understands — blocking the
call. A short-TTL in-memory cache keeps the hot path off the database; it
degrades **open** (never blocks) if the database is unavailable.
"""

from __future__ import annotations

import threading
import time
from contextvars import ContextVar
from typing import Optional

from core.context import get_current_user_id
from core.observability.logging import get_logger

logger = get_logger(__name__)

# Prompt tokens stashed between the paired input/output reports of one call.
_pending_input: ContextVar[int] = ContextVar("auth_cost_pending_input", default=0)

_CACHE_TTL = 30.0  # seconds a user's (cap, spend) stays cached on the hot path

_INSTALLED = False
_INSTALL_LOCK = threading.Lock()


try:  # the LLM service catches this type as a budget stop (not a generic error)
    from core.middleware.cost_control import BudgetExceededError
except Exception:  # noqa: BLE001 — define a local stand-in if core shape differs

    class BudgetExceededError(Exception):  # type: ignore[no-redef]
        """Raised to block an LLM call that would exceed a user's monthly cap."""


class _Budget:
    __slots__ = ("cap_micros", "spend_micros", "enforce", "warn_pct", "fetched_at")

    def __init__(
        self,
        cap_micros: Optional[int],
        spend_micros: int,
        enforce: bool,
        warn_pct: int,
        fetched_at: float,
    ) -> None:
        self.cap_micros = cap_micros
        self.spend_micros = spend_micros
        self.enforce = enforce
        self.warn_pct = warn_pct
        self.fetched_at = fetched_at


_cache: dict[str, _Budget] = {}
_cache_lock = threading.Lock()


def _persistence() -> object | None:
    """The auth persistence singleton, or ``None`` when DB is unavailable."""
    try:
        from plugins.auth.persistence import get_auth_persistence

        return get_auth_persistence()
    except Exception:  # noqa: BLE001 — DB-less deployments degrade gracefully
        return None


def _load_budget(user_id: str) -> Optional[_Budget]:
    """Fetch a user's cap + month-to-date spend from the DB (None on failure)."""
    # Admins are never limited — short-circuit to an uncapped budget so the
    # enforcement check always passes (their spend is still recorded for
    # visibility, just never blocked).
    from ._admin import is_unlimited_user

    if is_unlimited_user(user_id):
        return _Budget(None, 0, enforce=False, warn_pct=100, fetched_at=time.time())
    p = _persistence()
    if p is None:
        return None
    try:
        cap = p.effective_cap_micros(user_id)  # type: ignore[attr-defined]
        spend = p.monthly_spend_micros(user_id)  # type: ignore[attr-defined]
        policy = p.get_cost_policy()  # type: ignore[attr-defined]
        return _Budget(
            cap_micros=cap,
            spend_micros=int(spend),
            enforce=bool(policy.get("enforce", True)),
            warn_pct=int(policy.get("warn_threshold_pct", 80)),
            fetched_at=time.time(),
        )
    except Exception as exc:  # noqa: BLE001 — never block LLM on a DB hiccup
        logger.debug("cost budget load failed for %s: %s", user_id, exc)
        return None


def _budget(user_id: str) -> Optional[_Budget]:
    """Cached budget for a user, refreshed past the TTL."""
    now = time.time()
    with _cache_lock:
        cached = _cache.get(user_id)
        if cached is not None and now - cached.fetched_at < _CACHE_TTL:
            return cached
    fresh = _load_budget(user_id)
    if fresh is not None:
        with _cache_lock:
            _cache[user_id] = fresh
    return fresh


def _bump_cache_spend(user_id: str, delta_micros: int) -> None:
    """Reflect a just-recorded spend in the cache so enforcement stays current."""
    with _cache_lock:
        b = _cache.get(user_id)
        if b is not None:
            b.spend_micros += delta_micros


def _enforce(user_id: str) -> None:
    """Block the call if the user is at/over their enforced monthly cap."""
    b = _budget(user_id)
    if b is None or not b.enforce or not b.cap_micros:
        return
    if b.spend_micros >= b.cap_micros:
        raise BudgetExceededError(f"Monthly LLM budget exceeded for user {user_id}")


def _record(user_id: str, model: str, prompt: int, completion: int) -> None:
    """Persist one call's spend to the user's monthly ledger (best-effort)."""
    try:
        from core.models.pricing import estimate_cost

        spend_micros = int(round(estimate_cost(model, prompt, completion) * 1_000_000))
    except Exception:  # noqa: BLE001 — unknown model / pricing failure → skip cost
        spend_micros = 0
    p = _persistence()
    if p is None:
        return
    try:
        p.record_usage(  # type: ignore[attr-defined]
            user_id,
            spend_micros=spend_micros,
            prompt_tokens=prompt,
            completion_tokens=completion,
        )
        _bump_cache_spend(user_id, spend_micros)
    except Exception as exc:  # noqa: BLE001 — metering must never break a call
        logger.debug("cost record failed for %s: %s", user_id, exc)


def meter(count: int, model: str) -> None:
    """Handle one token report: enforce on input, record on output."""
    user_id = get_current_user_id()
    if not user_id:
        return  # background / unauthenticated → not metered, not capped
    if model.startswith("input"):
        _pending_input.set(int(count))
        _enforce(user_id)
        return
    prompt = _pending_input.get(0)
    if prompt:
        _pending_input.set(0)
    _record(user_id, model, prompt, int(count))


def install_user_cost_tracking() -> bool:
    """Wrap the core token sink to meter + enforce per-user spend (idempotent)."""
    global _INSTALLED
    if _INSTALLED:
        return True
    with _INSTALL_LOCK:
        if _INSTALLED:
            return True
        try:
            import core.services.llm.service as mod
        except Exception as exc:  # noqa: BLE001 — LLM layer optional
            logger.warning("auth cost tracking unavailable: %s", exc)
            return False
        original = getattr(mod, "_report_tokens_to_middleware", None)
        if not callable(original):
            return False

        def wrapped(count: int, model: str = "unknown") -> None:
            # Enforce first (may raise to block); only then forward + record.
            meter(count, model)
            original(count, model=model)

        mod._report_tokens_to_middleware = wrapped
        _INSTALLED = True
        logger.info("Auth per-user LLM cost tracking installed")
        return True


def invalidate_cache(user_id: Optional[str] = None) -> None:
    """Drop cached budgets (after an admin changes a cap or resets usage)."""
    with _cache_lock:
        if user_id is None:
            _cache.clear()
        else:
            _cache.pop(user_id, None)


__all__ = [
    "BudgetExceededError",
    "meter",
    "install_user_cost_tracking",
    "invalidate_cache",
]
