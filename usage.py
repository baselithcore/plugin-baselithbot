"""Forward the Node child's measured LLM usage to the host's token seam.

dbview's NL→Query and explain pipelines run inside the vendored Node child, so
every token they spend is invisible to this process — and the framework's
per-plugin cost ledger (the figure on the BaselithControl plugin card) only
learns about a call that is reported through
``core.services.llm.report_external_usage``. The child therefore stamps what its
providers reported on each response as ``x-dbview-llm-usage``
(``model;prompt;completion`` rows joined by ``,``; see
``apps/api/src/observability/llm-usage.store.ts``) and the proxy calls
:func:`report_upstream_usage` while the originating request is still in flight —
that is what makes the spend attributable to this plugin *and* to the
authenticated caller, both of which the host reads from the request context.

The header crosses a process boundary, so it is parsed defensively: anything
malformed is dropped rather than raised, the row count is capped, and counts are
bounded — a child that misbehaves must never break a proxied response or inject
an unbounded number of ledger rows.
"""

from __future__ import annotations

from collections.abc import Mapping

from core.observability.logging import get_logger

logger = get_logger(__name__)

#: Response header the child reports its per-request token usage on.
USAGE_HEADER = "x-dbview-llm-usage"

#: Ceiling on rows honoured from one response. A translate/explain round trip
#: makes a handful of LLM calls; anything beyond this is malformed or hostile.
_MAX_ROWS = 32
#: Ceiling on one reported count (≈ the largest context window, with room).
_MAX_COUNT = 100_000_000
_MAX_MODEL_CHARS = 120


def parse_usage(value: str | None) -> list[tuple[str, int, int]]:
    """Parse the header into ``(model, prompt_tokens, completion_tokens)`` rows.

    Returns an empty list for an absent, empty or malformed value; individual
    malformed rows are skipped without discarding the valid ones.
    """
    if not value or not value.strip():
        return []
    rows: list[tuple[str, int, int]] = []
    for raw_row in value.split(","):
        if len(rows) >= _MAX_ROWS:
            break
        parts = raw_row.split(";")
        if len(parts) != 3:
            continue
        model = parts[0].strip()[:_MAX_MODEL_CHARS]
        if not model:
            continue
        try:
            prompt = int(parts[1])
            completion = int(parts[2])
        except ValueError:
            continue
        if prompt < 0 or completion < 0:
            continue
        if prompt > _MAX_COUNT or completion > _MAX_COUNT:
            continue
        if prompt == 0 and completion == 0:
            continue
        rows.append((model, prompt, completion))
    return rows


def report_upstream_usage(headers: Mapping[str, str]) -> None:
    """Report the usage *headers* carry to the framework seam (never raises).

    Call from inside the request that produced the response: attribution to the
    plugin and to the authenticated caller comes from that request's context.
    """
    try:
        rows = parse_usage(headers.get(USAGE_HEADER))
        if not rows:
            return
        from core.services.llm import report_external_usage

        for model, prompt, completion in rows:
            report_external_usage(
                model, prompt_tokens=prompt, completion_tokens=completion
            )
    except Exception:  # noqa: BLE001 — accounting must never break the proxy
        logger.debug("[dbview] upstream LLM usage report failed", exc_info=True)


__all__ = ["USAGE_HEADER", "parse_usage", "report_upstream_usage"]
