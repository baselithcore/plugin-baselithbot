"""Threat Intel Extractors."""

import re
from typing import List


def extract_domains(text: str) -> List[str]:
    """Extract domain names from text."""
    pattern = r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"
    matches = re.findall(pattern, text)
    return list(set(matches))


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    pattern = r'https?://[^\s<>"\']+[^\s<>"\'.,;:!?\)\]\}]'
    matches = re.findall(pattern, text)
    return list(set(matches))
