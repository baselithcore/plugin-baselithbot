"""Threat Intel YARA Rule Generator."""

import re
from datetime import datetime
from typing import List, Set


def escape_for_yara(s: str) -> str:
    """Escape string for YARA rule."""
    # Escape special characters
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return s


def create_yara_rule(
    name: str,
    strings: List[str],
    description: str,
) -> str:
    """Create a YARA rule."""
    if not strings:
        return ""

    string_defs = []
    for i, s in enumerate(strings):
        string_defs.append(f'        $s{i} = "{s}"')

    return f'''rule {name}
{{
    meta:
        description = "{description}"
        author = "Honeypot Auto-Generator"
        date = "{datetime.now().strftime("%Y-%m-%d")}"

    strings:
{chr(10).join(string_defs)}

    condition:
        any of them
}}'''


def find_common_strings(payloads: List[str], min_len: int = 8) -> List[str]:
    """Find common strings across payloads."""
    if not payloads:
        return []

    # Extract all substrings from first payload
    first = payloads[0]
    candidates: Set[str] = set()

    # Extract printable string sequences
    for match in re.finditer(r"[\x20-\x7e]{8,50}", first):
        candidates.add(match.group())

    # Filter to those present in most payloads
    threshold = len(payloads) * 0.7
    common = []

    for candidate in candidates:
        count = sum(1 for p in payloads if candidate in p)
        if count >= threshold:
            # Escape special chars for YARA
            escaped = escape_for_yara(candidate)
            common.append(escaped)

    # Return top strings by length (longer = more specific)
    return sorted(common, key=len, reverse=True)[:5]
