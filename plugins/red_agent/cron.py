"""Minimal 5-field cron parser used by the schedule dispatcher.

Standard cron syntax: ``minute hour day month dow``. Each field accepts:

* ``*``                   — any value
* a single integer        — exact match
* ``a-b``                 — inclusive range
* ``a,b,c``               — list of any of the above
* ``*/n``                 — every ``n`` units within the field's bounds

Day-of-week uses 0-6 with 0 = Sunday (POSIX). Day-of-month and day-of-week
follow the classic cron OR semantics: when both are restricted, the slot
fires when *either* matches.

We deliberately avoid a third-party dep — the dispatcher only needs
"is this minute a match?" and "find the next firing on or after now".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


_FIELD_BOUNDS = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))


def _parse_field(token: str, lo: int, hi: int) -> set[int]:
    out: set[int] = set()
    for part in token.split(","):
        step = 1
        if "/" in part:
            base, _, step_s = part.partition("/")
            step = int(step_s)
        else:
            base = part
        if base == "*" or base == "":
            start, end = lo, hi
        elif "-" in base:
            a_s, _, b_s = base.partition("-")
            start, end = int(a_s), int(b_s)
        else:
            start = end = int(base)
        if start < lo or end > hi or start > end or step < 1:
            raise ValueError(f"cron field out of range: {token}")
        out.update(range(start, end + 1, step))
    return out


@dataclass
class CronExpr:
    minutes: set[int]
    hours: set[int]
    days: set[int]
    months: set[int]
    dows: set[int]
    dom_restricted: bool
    dow_restricted: bool

    @classmethod
    def parse(cls, expr: str) -> "CronExpr":
        parts = expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"cron expression must have 5 fields: {expr!r}")
        sets = [
            _parse_field(p, lo, hi)
            for p, (lo, hi) in zip(parts, _FIELD_BOUNDS, strict=True)
        ]
        return cls(
            minutes=sets[0],
            hours=sets[1],
            days=sets[2],
            months=sets[3],
            dows=sets[4],
            dom_restricted=parts[2] != "*",
            dow_restricted=parts[4] != "*",
        )

    def matches(self, dt: datetime) -> bool:
        if dt.minute not in self.minutes:
            return False
        if dt.hour not in self.hours:
            return False
        if dt.month not in self.months:
            return False
        # POSIX cron: when both day-of-month and day-of-week are restricted,
        # the schedule fires if EITHER matches (OR semantics).
        dom_ok = dt.day in self.days
        dow_ok = ((dt.weekday() + 1) % 7) in self.dows
        if self.dom_restricted and self.dow_restricted:
            return dom_ok or dow_ok
        if self.dom_restricted:
            return dom_ok
        if self.dow_restricted:
            return dow_ok
        return True


def next_after(
    expr: CronExpr, after: datetime, *, max_minutes: int = 366 * 24 * 60
) -> datetime:
    """Return the first minute strictly after ``after`` that matches.

    Walks one minute at a time — fine for the dispatcher (called once per
    schedule, typically once a day). Capped at one year to bound the loop.
    """
    cursor = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(max_minutes):
        if expr.matches(cursor):
            return cursor
        cursor += timedelta(minutes=1)
    raise ValueError("cron expression has no firing within a year")


def is_due(expr_str: str, *, now: datetime, last_fired_at: datetime | None) -> bool:
    """Return True when ``now`` is at or past the next firing after ``last_fired_at``.

    Tolerates malformed expressions (returns False) so a single bad cron does
    not crash the dispatcher loop.
    """
    try:
        expr = CronExpr.parse(expr_str)
    except ValueError:
        return False
    anchor = last_fired_at or now - timedelta(minutes=2)
    try:
        nxt = next_after(expr, anchor.astimezone(timezone.utc))
    except ValueError:
        return False
    return now >= nxt
