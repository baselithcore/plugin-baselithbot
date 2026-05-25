"""Fingerprint Profiles Package.

Provides YAML-based OS fingerprint profiles for sophisticated emulation.
"""

from pathlib import Path

PROFILES_DIR = Path(__file__).parent


def get_available_profiles() -> list[str]:
    """Get list of available profile names.

    Returns:
        List of profile names (without .yaml extension)
    """
    return [p.stem for p in PROFILES_DIR.glob("*.yaml") if not p.name.startswith("_")]
