"""ML / LLM enrichment configuration mixins."""

from __future__ import annotations

from pydantic import BaseModel, Field


class _LLMTriageConfig(BaseModel):
    llm_triage_enabled: bool = Field(
        default=False,
        description=(
            "Run findings through an LLM triage pass: re-evaluate severity, "
            "mark false positives, synthesize remediation. Fail-open: any "
            "LLM error returns the original findings untouched."
        ),
    )
    llm_triage_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description=(
            "Model used for LLM triage. Haiku-class models are sized for "
            "the per-finding classification workload; switch to Sonnet for "
            "richer remediation prose."
        ),
    )
    llm_triage_batch_size: int = Field(
        default=5,
        description="Findings per LLM triage call. Tune to balance latency vs context budget.",
    )
    llm_triage_drop_false_positives: bool = Field(
        default=True,
        description=(
            "When the LLM triage marks a finding as false_positive with "
            "confidence above the override threshold, drop it from the "
            "scan result. Set false to keep them and only annotate."
        ),
    )
    llm_triage_min_confidence_to_override: float = Field(
        default=0.8,
        description=(
            "Minimum LLM confidence required to mutate severity or to drop "
            "a false-positive finding. Below this the verdict is recorded "
            "in evidence but the finding is preserved unchanged."
        ),
    )


class _SemanticDedupConfig(BaseModel):
    semantic_dedup_enabled: bool = Field(
        default=False,
        description=(
            "Cross-scan semantic dedup of findings via Qdrant. New findings "
            "are embedded and checked against the per-target collection; "
            "matches above the threshold are linked to the prior finding "
            "instead of being persisted as new."
        ),
    )
    semantic_dedup_collection: str = Field(
        default="red_agent_findings",
        description="Qdrant collection name for finding embeddings.",
    )
    semantic_dedup_threshold: float = Field(
        default=0.92,
        description=(
            "Cosine similarity threshold above which two findings are "
            "considered the same. 0.92 is conservative — tune downward only "
            "after measuring false-merge rate on real triage data."
        ),
    )


class _MLClassifierConfig(BaseModel):
    ml_fp_classifier_enabled: bool = Field(
        default=False,
        description=(
            "Apply the ML false-positive classifier to every finding. "
            "Requires a model artifact at ``ml_fp_classifier_model_path``; "
            "absent file = service runs in disabled mode."
        ),
    )
    ml_fp_classifier_model_path: str = Field(
        default="./var/red_agent/models/fp_classifier.joblib",
        description="Filesystem path to the joblib-serialized FP classifier.",
    )
    ml_fp_classifier_drop_threshold: float = Field(
        default=0.85,
        description=(
            "Findings with predicted FP probability ≥ this threshold are "
            "dropped from the scan result. The score is recorded under "
            "``Finding.evidence['ml_fp_score']`` regardless of the drop."
        ),
    )

    ml_anomaly_detector_enabled: bool = Field(
        default=False,
        description=(
            "Run a background task that scores recent agent_telemetry "
            "windows with an Isolation Forest. Anomalies materialize as "
            "synthetic findings (scanner='ml_anomaly')."
        ),
    )
    ml_anomaly_window_minutes: int = Field(
        default=15,
        description="Rolling-window size used to aggregate per-host telemetry features.",
    )
    ml_anomaly_tick_seconds: int = Field(
        default=300,
        description="Interval between detector ticks. 300s = quarter-window cadence.",
    )
    ml_anomaly_contamination: float = Field(
        default=0.02,
        description=(
            "Expected anomaly fraction passed to IsolationForest. 2% is a "
            "sane default for production fleets — lower means stricter."
        ),
    )
    ml_anomaly_min_samples: int = Field(
        default=20,
        description="Skip scoring until this many samples are present in the window.",
    )
