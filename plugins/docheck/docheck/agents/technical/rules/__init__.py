"""Built-in deterministic rule registry."""

from __future__ import annotations

from .._base import Rule
from .dates import DateIsoRule
from .fiscal_id import CodiceFiscaleRule, PartitaIvaRule
from .iban import IbanRule
from .legal_refs import LegalRefMalformedRule
from .postal import CapItRule


def all_rules() -> list[Rule]:
    """Instantiation order = evaluation order. Order is stable for reproducibility."""
    return [
        DateIsoRule(),
        CodiceFiscaleRule(),
        PartitaIvaRule(),
        IbanRule(),
        CapItRule(),
        LegalRefMalformedRule(),
    ]


__all__ = [
    "CapItRule",
    "CodiceFiscaleRule",
    "DateIsoRule",
    "IbanRule",
    "LegalRefMalformedRule",
    "PartitaIvaRule",
    "all_rules",
]
