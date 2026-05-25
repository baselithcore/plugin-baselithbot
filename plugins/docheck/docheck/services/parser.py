"""Compatibility shim. Real parsers live in `parsers/` package."""

from .parsers import parse

__all__ = ["parse"]
