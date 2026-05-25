"""Adversary-emulation configuration mixin.

Emulation runs real adversary techniques on enrolled endpoints.
Three properties follow:

1. **Off by default.** Operators must opt in per engagement; the
   master toggle ``adversary_emulation_enabled`` is required. Plans
   never auto-execute — they always go through the
   signed-policy-bundle review and the dual-control approval flow.
2. **Signed plans only.** ``require_signed_plan`` rejects any plan
   that has not been signed by an authorized reviewer. Disabling
   this is intended only for closed labs.
3. **Cleanup on by default.** ``always_run_cleanup`` forces every
   step's ``cleanup_command`` to run regardless of the plan-author's
   request. Operators who genuinely need a forensic pause flip the
   per-step ``require_cleanup`` instead, which is captured in the
   audit trail.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class _AdversaryConfig(BaseModel):
    adversary_emulation_enabled: bool = Field(
        default=False,
        description=(
            "Master toggle for the adversary-emulation backends. When "
            "false the plan loader, the Atomic dispatcher, and the "
            "Caldera client all refuse to run."
        ),
    )
    adversary_require_signed_plan: bool = Field(
        default=True,
        description=(
            "Reject any :class:`EmulationPlan` that has not been "
            "signed via the existing policy-bundle pipeline. Off only "
            "in lab environments."
        ),
    )
    adversary_require_dual_control: bool = Field(
        default=True,
        description=(
            "Reject plans whose ``reviewed_by`` field is empty or "
            "matches ``authored_by``. Defends against a single "
            "compromised operator pushing a destructive plan."
        ),
    )
    adversary_always_run_cleanup: bool = Field(
        default=True,
        description=(
            "Force every step to run its Atomic cleanup command "
            "regardless of plan-author preference. Off only with an "
            "explicit forensic-capture flag."
        ),
    )
    adversary_atomics_root: str | None = Field(
        default=None,
        description=(
            "Filesystem path to a checkout of "
            "``redcanaryco/atomic-red-team``. Required when the plan "
            "loader uses the Atomic backend; CI keeps the mirror "
            "current."
        ),
    )
    adversary_caldera_base_url: str | None = Field(
        default=None,
        description=(
            "Base URL of the Caldera server (e.g. "
            "``https://caldera.internal:8443``). Required when the "
            "Caldera backend is selected."
        ),
    )
    adversary_caldera_api_key: SecretStr | None = Field(
        default=None,
        description="Caldera API key passed via the ``KEY`` header.",
    )
    adversary_caldera_request_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP timeout per Caldera REST call.",
    )
    adversary_max_steps_per_plan: int = Field(
        default=50,
        description=(
            "Hard ceiling on plan size — protects the daemon "
            "executor from runaway plans and bounds the audit "
            "footprint."
        ),
    )
    adversary_step_default_timeout_seconds: int = Field(
        default=120,
        description=(
            "Default per-step wall-clock cap when the plan does not supply one."
        ),
    )
