"""Models for variant analysis — the process-mining "variant explorer".

A *variant* is one distinct end-to-end path through a process. Celonis/Signavio
treat the variant table as the primary lens on an event log: which paths dominate,
which are rare deviations, and how throughput/cost differ between them. These
models carry that richer per-variant view (share, throughput percentiles, model
conformance, cost) beyond the basic counts already surfaced by mining.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._stats import Distribution


class VariantDetail(BaseModel):
    """One distinct path through the process and how it actually performs."""

    id: str = Field(..., description="Stable short fingerprint of the path.")
    sequence: list[str] = Field(..., description="Ordered activity names.")
    count: int = Field(..., description="Cases that followed this exact path.")
    share: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Fraction of all cases (0..1)."
    )
    duration: Distribution = Field(
        ..., description="Throughput-time distribution for this variant's cases."
    )
    conforms: bool = Field(
        default=True,
        description="Whether every transition in the path is allowed by the model.",
    )
    deviation_count: int = Field(
        default=0, description="Transitions in the path the model does not allow."
    )
    cost_per_case: float = Field(
        default=0.0, description="Summed model node cost across the path's steps."
    )
    is_happy_path: bool = Field(
        default=False,
        description="The most frequent conforming variant (the reference path).",
    )


class VariantReport(BaseModel):
    """The full variant breakdown of an event log against a process model."""

    process_id: str
    case_count: int = Field(..., description="Distinct cases analysed.")
    variant_count: int = Field(..., description="Distinct paths observed.")
    happy_path_id: str | None = Field(
        default=None, description="Id of the reference (most common conforming) path."
    )
    conforming_cases: int = Field(
        default=0, description="Cases whose path the model fully allows."
    )
    deviating_cases: int = Field(
        default=0, description="Cases whose path leaves the model."
    )
    rare_variant_count: int = Field(
        default=0, description="Variants below the rare-share threshold."
    )
    currency: str = Field(default="EUR", description="Currency for cost_per_case.")
    variants: list[VariantDetail] = Field(default_factory=list)


class VariantDiff(BaseModel):
    """Side-by-side comparison of two variants (deltas are b − a)."""

    a_id: str
    b_id: str
    a_sequence: list[str]
    b_sequence: list[str]
    added_steps: list[str] = Field(
        default_factory=list, description="Activities in b but not a."
    )
    removed_steps: list[str] = Field(
        default_factory=list, description="Activities in a but not b."
    )
    shared_steps: list[str] = Field(default_factory=list)
    count_delta: int = Field(default=0, description="Case-count difference (b − a).")
    cycle_time_p50_delta: float = Field(default=0.0, description="Median Δ seconds.")
    cycle_time_p90_delta: float = Field(default=0.0, description="P90 Δ seconds.")
    cost_delta: float = Field(default=0.0, description="Per-case cost Δ.")
    currency: str = Field(default="EUR")


__all__ = ["VariantDetail", "VariantReport", "VariantDiff"]
