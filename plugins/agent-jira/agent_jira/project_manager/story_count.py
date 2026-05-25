from __future__ import annotations

import re
from typing import Optional

_NUMBER_WORDS = {
    "un": 1,
    "uno": 1,
    "una": 1,
    "one": 1,
    "due": 2,
    "two": 2,
    "tre": 3,
    "three": 3,
    "quattro": 4,
    "four": 4,
    "cinque": 5,
    "five": 5,
    "sei": 6,
    "six": 6,
    "sette": 7,
    "seven": 7,
    "otto": 8,
    "eight": 8,
    "nove": 9,
    "nine": 9,
    "dieci": 10,
    "ten": 10,
    "undici": 11,
    "eleven": 11,
    "dodici": 12,
    "twelve": 12,
    "tredici": 13,
    "thirteen": 13,
    "quattordici": 14,
    "fourteen": 14,
    "quindici": 15,
    "fifteen": 15,
    "sedici": 16,
    "sixteen": 16,
    "diciassette": 17,
    "seventeen": 17,
    "diciotto": 18,
    "eighteen": 18,
    "diciannove": 19,
    "nineteen": 19,
    "venti": 20,
    "twenty": 20,
}

_STORY_COUNT_PATTERN = re.compile(
    r"\b(?P<count>\d+|"
    + "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True))
    + r")\b\s*(?:user\s*)?(?:stories|story|storie(?:\s+utente)?|storia(?:\s+utente)?)\b",
    re.IGNORECASE,
)


def parse_requested_story_count(
    text: str,
    *,
    default: Optional[int] = None,
    min_value: int = 1,
    max_value: int = 20,
) -> Optional[int]:
    if not text:
        return default

    match = _STORY_COUNT_PATTERN.search(text)
    if not match:
        return default

    raw_count = match.group("count").strip().lower()
    if raw_count.isdigit():
        value = int(raw_count)
    else:
        value = _NUMBER_WORDS.get(raw_count)

    if value is None or value < min_value or value > max_value:
        return default
    return value
