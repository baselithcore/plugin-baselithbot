"""TechnicalComplianceAgent package — DocCheck_Builtin deterministic rules.

Public API kept stable for graph wiring and PII agent regex sharing:
    - `run(state)`: graph node entrypoint.
    - `PATTERNS`: shared regex dict (consumed by pii agent).
"""

from .engine import run
from .patterns import PATTERNS

__all__ = ["PATTERNS", "run"]
