"""Entropy and printable-string extraction for the binary analyzer.

Pure stdlib. Operates on raw bytes without ever executing the sample.
"""

from __future__ import annotations

import math
from collections import Counter

# Minimum printable run length, matching the ``strings`` Unix utility default.
MIN_STRING_LEN = 6
ASCII_RANGE = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}


def shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits/byte. 0 = constant, 8 = uniform random.

    Sections above 7.0 are typically packed/encrypted.
    """
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def extract_strings(data: bytes, *, min_len: int = MIN_STRING_LEN) -> list[str]:
    """Extract printable ASCII and UTF-16-LE string runs."""
    out: list[str] = []
    cur: list[int] = []
    for b in data:
        if b in ASCII_RANGE:
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(bytes(cur).decode("ascii", errors="replace"))
            cur = []
    if len(cur) >= min_len:
        out.append(bytes(cur).decode("ascii", errors="replace"))

    # UTF-16-LE: ascii byte followed by 0x00.
    cur = []
    i = 0
    n = len(data)
    while i + 1 < n:
        lo, hi = data[i], data[i + 1]
        if hi == 0 and lo in ASCII_RANGE:
            cur.append(lo)
            i += 2
            continue
        if len(cur) >= min_len:
            out.append(bytes(cur).decode("ascii", errors="replace"))
        cur = []
        i += 1
    if len(cur) >= min_len:
        out.append(bytes(cur).decode("ascii", errors="replace"))
    return out
