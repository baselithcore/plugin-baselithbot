"""Similarity computation logic."""

import math
from typing import List, Set

try:
    import ssdeep

    HAS_SSDEEP = True
except ImportError:
    HAS_SSDEEP = False
    ssdeep = None


def compute_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(v1) != len(v2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a**2 for a in v1))
    norm2 = math.sqrt(sum(b**2 for b in v2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def compute_payload_similarity(payload1: str, payload2: str) -> float:
    """Compute fuzzy similarity between two payloads."""
    if not payload1 or not payload2:
        return 0.0

    if HAS_SSDEEP:
        try:
            hash1 = ssdeep.hash(payload1.encode())
            hash2 = ssdeep.hash(payload2.encode())
            return ssdeep.compare(hash1, hash2) / 100.0
        except Exception:
            pass

    # Fallback: Jaccard similarity on 3-grams
    def get_ngrams(text: str, n: int = 3) -> Set[str]:
        return {text[i : i + n] for i in range(len(text) - n + 1)}

    ngrams1 = get_ngrams(payload1)
    ngrams2 = get_ngrams(payload2)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    return intersection / union if union > 0 else 0.0
