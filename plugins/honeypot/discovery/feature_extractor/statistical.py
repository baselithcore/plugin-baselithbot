"""Statistical feature extraction."""

import re
from typing import List

from ...models import AttackEvent
from .models import AttackFeatureVector
from .utils import get_payload


def extract_statistical_features(
    features: AttackFeatureVector, events: List[AttackEvent]
) -> None:
    """Extract statistical content features."""
    all_content = ""
    hex_patterns = 0
    url_count = 0
    ip_count = 0

    for event in events:
        content = get_payload(event)
        all_content += content

        # Count hex patterns
        hex_patterns += len(re.findall(r"\\x[0-9a-fA-F]{2}", content))
        hex_patterns += len(re.findall(r"0x[0-9a-fA-F]+", content))

        # Count URLs
        url_count += len(re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content))

        # Count IP references
        ip_count += len(re.findall(r"\d+\.\d+\.\d+\.\d+", content))

    features.hex_pattern_count = hex_patterns
    features.url_count = url_count
    features.ip_reference_count = ip_count

    # Special character ratio
    if all_content:
        special_chars = sum(
            1 for c in all_content if not c.isalnum() and not c.isspace()
        )
        features.special_char_ratio = special_chars / len(all_content)
