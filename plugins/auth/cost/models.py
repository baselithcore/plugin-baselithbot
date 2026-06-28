"""DTOs + money helpers for per-user LLM cost governance.

Money is stored as integer **micro-USD** (1 USD = 1_000_000) end to end and only
converted to/from float USD at the API boundary, so accumulation stays exact.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

MICROS_PER_USD = 1_000_000


def usd_to_micros(usd: Optional[float]) -> Optional[int]:
    """Convert a USD amount to micro-USD (``None`` = unlimited, passed through)."""
    if usd is None:
        return None
    return int(round(usd * MICROS_PER_USD))


def micros_to_usd(micros: Optional[int]) -> Optional[float]:
    """Convert micro-USD to USD (``None`` stays ``None``)."""
    if micros is None:
        return None
    return round(micros / MICROS_PER_USD, 6)


class UsageStatus(str, Enum):
    """Where a user sits against their cap."""

    ok = "ok"
    warning = "warning"  # at/above the warn threshold (e.g. 80%)
    blocked = "blocked"  # at/above 100% — calls are denied when enforcing


def compute_status(
    spend_micros: int, cap_micros: Optional[int], warn_pct: int
) -> tuple[UsageStatus, Optional[int]]:
    """Return ``(status, percent_used)`` — percent is ``None`` when uncapped."""
    if not cap_micros or cap_micros <= 0:
        return UsageStatus.ok, None
    pct = int(spend_micros * 100 / cap_micros)
    if pct >= 100:
        return UsageStatus.blocked, pct
    if pct >= warn_pct:
        return UsageStatus.warning, pct
    return UsageStatus.ok, pct


class CostPolicyView(BaseModel):
    """The org-wide default cost policy."""

    monthly_cap_usd: Optional[float] = None  # None = unlimited by default
    warn_threshold_pct: int = 80
    enforce: bool = True


class CostPolicyUpdate(BaseModel):
    """Admin update to the org-wide cost policy."""

    monthly_cap_usd: Optional[float] = Field(default=None, ge=0)
    warn_threshold_pct: int = Field(default=80, ge=1, le=100)
    enforce: bool = True


class CapUpdate(BaseModel):
    """Set (or clear, with ``null``) a per-user / per-group monthly cap."""

    monthly_cap_usd: Optional[float] = Field(default=None, ge=0)


class MyUsageView(BaseModel):
    """The current user's own spend vs cap, for the self-service panel."""

    period: str  # ISO date of the month start (e.g. 2026-06-01)
    currency: str = "USD"
    spend_usd: float = 0.0
    cap_usd: Optional[float] = None  # None = unlimited
    percent_used: Optional[int] = None
    status: UsageStatus = UsageStatus.ok
    warn_threshold_pct: int = 80
    enforce: bool = True


class UserUsageRow(BaseModel):
    """One user's spend + effective cap for the admin overview."""

    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    spend_usd: float = 0.0
    request_count: int = 0
    cap_usd: Optional[float] = None  # effective (user > group > global)
    user_cap_usd: Optional[float] = None  # explicit per-user override, if any
    percent_used: Optional[int] = None
    status: UsageStatus = UsageStatus.ok


class AdminUsageView(BaseModel):
    """Per-user usage table for the admin budget tab."""

    period: str
    currency: str = "USD"
    warn_threshold_pct: int = 80
    rows: list[UserUsageRow] = Field(default_factory=list)


__all__ = [
    "MICROS_PER_USD",
    "usd_to_micros",
    "micros_to_usd",
    "UsageStatus",
    "compute_status",
    "CostPolicyView",
    "CostPolicyUpdate",
    "CapUpdate",
    "MyUsageView",
    "UserUsageRow",
    "AdminUsageView",
]
