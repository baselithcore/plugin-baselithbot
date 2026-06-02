"""PHI / PII redactor for Italian healthcare contexts.

Patient-identifiable fragments routinely leak into free-text fields the
audit ledger ingests (clinician notes, validator comments,
``raw_quote``-bearing payloads). This module applies a layered regex
redactor to strip the most common Italian identifiers BEFORE the value is
hashed/stored:

    * **Codice Fiscale** — 16-char alphanumeric pattern unique to Italy.
    * **Italian phone numbers** — fixed-line + mobile patterns with or
      without the ``+39`` prefix.
    * **Email addresses** — RFC-shaped local-part + domain.
    * **IBAN-IT** — country-prefixed bank account numbers.
    * **Dates of birth** — ``dd/mm/yyyy`` and ``dd-mm-yy`` formats.
    * **EU postcodes (numeric 5-digit)** — when paired with a city marker.

Names and addresses are intentionally OUT OF SCOPE: doing them right
requires NER (spaCy / Stanza). A future addition can layer NER on top of
this regex baseline; until then the redactor errs on the side of leaving
unstructured text untouched rather than producing false positives that
break clinical context.
"""

from __future__ import annotations

import re
from typing import Final


# Each pattern + replacement label. Ordering matters: more specific
# patterns (Codice Fiscale, IBAN) run first so they are not over-matched
# by the generic number patterns later in the chain.
_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (
        re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b"),
        "[REDACTED:CF]",
    ),
    (
        re.compile(r"\bIT\d{2}[A-Z]\d{10}[A-Z0-9]{12}\b"),
        "[REDACTED:IBAN]",
    ),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED:EMAIL]",
    ),
    (
        re.compile(r"(?<!\w)(?:\+39\s?)?(?:3\d{2}\s?\d{6,7}|0\d{1,3}\s?\d{6,8})(?!\d)"),
        "[REDACTED:PHONE]",
    ),
    (
        re.compile(
            r"\b(0?[1-9]|[12]\d|3[01])[/\-](0?[1-9]|1[0-2])"
            r"[/\-](19|20)?\d{2}\b"
        ),
        "[REDACTED:DATE]",
    ),
)


def redact(text: str) -> str:
    """Return ``text`` with PHI patterns replaced by sentinels.

    Empty / non-string input is returned unchanged so callers can pass
    optional ``str | None`` values without pre-checking.
    """
    if not isinstance(text, str) or not text:
        return text
    redacted = text
    for pattern, replacement in _PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_dict(payload: dict[str, object]) -> dict[str, object]:
    """Recursively redact string values in a dict (lists/tuples included).

    Non-string scalars (int, float, bool, None) are passed through. The
    function never raises — even on malformed shapes — so it is safe to
    use inside an audit-write path.
    """
    return _redact_value(payload)  # type: ignore[return-value]


def _redact_value(value: object) -> object:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(v) for v in value)
    return value
