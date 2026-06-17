"""FIA sporting-regulation guardrail — an isolated output validator.

This layer is deliberately decoupled from the decision logic: the swarm and the
MCTS simulator decide *what* is fastest; the guardrail decides whether that move
is *legal*. It is a pure function of (candidate action, belief state, race
context) and the declarative rules in ``fia_rules/``. A blocking verdict vetoes
a recommendation regardless of how attractive the simulator found it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from core.observability.logging import get_logger

from .models import FIAVerdict, RecommendationKind, StintState, TyreCompound

logger = get_logger(__name__)

_RULES_DIR = Path(__file__).resolve().parent / "fia_rules"


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, Any]:
    """Load and cache the sporting-code parameters; degrade to safe defaults."""
    path = _RULES_DIR / "sporting_code.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:  # pragma: no cover - fs/parse guard
        logger.warning("fia_rules_load_failed", error=str(exc))
        data = {}
    return data if isinstance(data, dict) else {}


class RaceContext:
    """Race-level facts the guardrail needs that a single stint cannot supply."""

    def __init__(
        self,
        compounds_used: set[str] | None = None,
        is_dry: bool = True,
        pit_compound: str | None = None,
    ) -> None:
        self.compounds_used = compounds_used or set()
        self.is_dry = is_dry
        # Compound the candidate PIT action would fit (if any).
        self.pit_compound = pit_compound


class FIAGuardrail:
    """Validates a candidate recommendation against the sporting regulations."""

    def __init__(self) -> None:
        self._rules = _load_rules()

    def validate(
        self,
        kind: RecommendationKind,
        stint: StintState,
        context: RaceContext,
    ) -> FIAVerdict:
        """Return a compliance verdict for the candidate action."""
        violations: list[str] = []
        notes: list[str] = []

        if kind is RecommendationKind.PIT_NOW:
            self._check_pit(stint, context, violations, notes)
        elif kind in (RecommendationKind.STAY_OUT, RecommendationKind.HOLD):
            self._check_no_stop(stint, context, violations)

        self._check_stint_length(stint, notes)

        return FIAVerdict(compliant=not violations, violations=violations, notes=notes)

    # -- individual checks -------------------------------------------------

    def _check_pit(
        self,
        stint: StintState,
        context: RaceContext,
        violations: list[str],
        notes: list[str],
    ) -> None:
        """Pit-lap legality and compound legality for a candidate stop."""
        min_lap = int(self._rules.get("min_pit_lap", 1))
        if stint.lap < min_lap:
            violations.append(f"Pit before legal lap {min_lap} (lap {stint.lap}).")
        target = context.pit_compound
        if target is not None:
            legal = (
                self._rules.get("dry_legal_compounds", [])
                if context.is_dry
                else self._rules.get("wet_legal_compounds", [])
            )
            if target not in legal:
                violations.append(
                    f"Compound '{target}' is not legal for the declared "
                    f"{'dry' if context.is_dry else 'wet'} race."
                )
            else:
                notes.append(f"Fitting {target} satisfies compound legality.")

    def _check_no_stop(
        self,
        stint: StintState,
        context: RaceContext,
        violations: list[str],
    ) -> None:
        """Mandatory two-compound rule when electing not to stop near the end."""
        if not self._rules.get("mandatory_compound_change", False):
            return
        if not context.is_dry:
            return
        # Only a problem if the race is ending and the rule is unmet.
        distinct = {c for c in context.compounds_used} | {stint.compound.value}
        dry_legal = set(self._rules.get("dry_legal_compounds", []))
        distinct_dry = distinct & dry_legal
        if stint.laps_remaining <= 2 and len(distinct_dry) < 2:
            violations.append(
                "Mandatory compound change unmet: a second dry compound must "
                "still be used before the flag."
            )

    def _check_stint_length(self, stint: StintState, notes: list[str]) -> None:
        """Advisory note when a stint exceeds the recommended length."""
        advisory = self._rules.get("advisory_max_stint_laps", {})
        try:
            limit = int(advisory.get(stint.compound.value))
        except (TypeError, ValueError):
            return
        if stint.tyre_age_laps > limit:
            notes.append(
                f"{stint.compound.value} stint at {stint.tyre_age_laps} laps "
                f"exceeds advisory {limit}."
            )

    @staticmethod
    def legal_dry_compounds() -> list[str]:
        """Expose the legal dry compounds for the recommender's pit choice."""
        rules = _load_rules()
        return list(rules.get("dry_legal_compounds", [c.value for c in TyreCompound]))


__all__ = ["FIAGuardrail", "RaceContext"]
