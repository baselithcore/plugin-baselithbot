"""Honeypot Suggester Package.

Analyzes attack patterns to suggest custom honeypots for discovering
emerging attack techniques not yet cataloged as CVEs.
"""

from .models import HoneypotSuggestion, SuggestionSummary
from .core import HoneypotSuggestionEngine

__all__ = [
    "HoneypotSuggestion",
    "SuggestionSummary",
    "HoneypotSuggestionEngine",
]
