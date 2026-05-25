"""Advanced Deception System Configuration Classes.

Configuration for emulation, ML, and cluster features.
"""

from typing import List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings
from core.config.env import PROJECT_ENV_FILE


class EmulationConfig(BaseSettings):
    """Advanced emulation configuration for sophisticated deception.

    Controls fingerprint accuracy, latency simulation, and session state
    management for the Advanced Deception System.
    """

    model_config = {
        "env_prefix": "HONEYPOT_EMULATION_",
        "env_file": str(PROJECT_ENV_FILE),
        "extra": "ignore",
    }

    enabled: bool = Field(
        default=True,
        description="Enable advanced stateful emulation",
    )
    default_os_profile: str = Field(
        default="linux_ubuntu",
        description="Default OS profile for fingerprinting (linux_ubuntu, linux_centos, windows_server)",
    )
    fingerprint_strictness: Literal["low", "medium", "high"] = Field(
        default="high",
        description="How strictly to enforce fingerprint coherence",
    )

    # Latency simulation
    enable_latency_simulation: bool = Field(
        default=True,
        description="Enable realistic latency simulation",
    )
    enable_adaptive_latency: bool = Field(
        default=True,
        description="Adapt latency based on attacker speed (slow down automated tools)",
    )
    latency_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        le=5.0,
        description="Global multiplier for all simulated latencies",
    )

    # Session state
    session_state_ttl_minutes: int = Field(
        default=60,
        description="How long to retain session state in memory",
    )
    max_mutations_per_session: int = Field(
        default=1000,
        description="Maximum filesystem mutations to track per session",
    )

    # Bait generation
    enable_dynamic_baits: bool = Field(
        default=True,
        description="Enable ML-driven dynamic bait generation",
    )
    bait_credential_templates: List[str] = Field(
        default_factory=lambda: [
            "/etc/shadow",
            "~/.ssh/id_rsa",
            "~/.aws/credentials",
            "~/.kube/config",
        ],
        description="Paths to generate fake credentials for bait",
    )


class MLConfig(BaseSettings):
    """Machine Learning module configuration for TTP prediction.

    Controls the ML pipeline for predicting attacker Tactics, Techniques,
    and Procedures (TTPs) and generating adaptive responses.
    """

    model_config = {
        "env_prefix": "HONEYPOT_ML_",
        "env_file": str(PROJECT_ENV_FILE),
        "extra": "ignore",
    }

    enabled: bool = Field(
        default=True,  # Enabled with baseline model
        description="Enable ML-based TTP prediction",
    )
    model_path: str = Field(
        default="data/models/ttp_predictor_baseline.joblib",
        description="Path to trained TTP prediction model (relative to plugin dir)",
    )
    prediction_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for TTP predictions",
    )
    max_inference_time_ms: float = Field(
        default=50.0,
        description="Maximum time for ML inference (p99 budget)",
    )

    # Feature extraction
    command_history_window: int = Field(
        default=20,
        description="Number of recent commands to analyze for prediction",
    )
    enable_timing_features: bool = Field(
        default=True,
        description="Include timing features in prediction",
    )

    # Training
    training_enabled: bool = Field(
        default=False,
        description="Enable continuous model training",
    )
    training_batch_size: int = Field(
        default=100,
        description="Events per training batch",
    )
    training_interval_minutes: int = Field(
        default=60,
        description="Interval between training runs",
    )
    min_training_samples: int = Field(
        default=500,
        description="Minimum samples before training starts",
    )


class ClusterConfig(BaseSettings):
    """Cluster persistence configuration for multi-node coherence.

    Controls state synchronization across multiple honeypot nodes
    to maintain consistent environment during lateral movement simulation.
    """

    model_config = {
        "env_prefix": "HONEYPOT_CLUSTER_",
        "env_file": str(PROJECT_ENV_FILE),
        "extra": "ignore",
    }

    enabled: bool = Field(
        default=True,  # Enabled - FalkorDB/Redis available
        description="Enable cluster mode for multi-node state sync",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for cluster state backend",
    )
    node_id: Optional[str] = Field(
        default=None,
        description="Unique node identifier (auto-generated if not set)",
    )
    region: str = Field(
        default="us-east-1",
        description="Cloud region for simulated environment",
    )

    # State synchronization
    state_sync_interval_ms: int = Field(
        default=100,
        description="State sync interval in milliseconds",
    )
    session_ttl_minutes: int = Field(
        default=60,
        description="Session state TTL in cluster (Redis)",
    )
    mutation_history_limit: int = Field(
        default=500,
        description="Maximum mutations to store per session in cluster",
    )

    # Pub/Sub channels
    state_channel: str = Field(
        default="honeypot:cluster:state",
        description="Redis pub/sub channel for state updates",
    )
    event_channel: str = Field(
        default="honeypot:cluster:events",
        description="Redis pub/sub channel for attack events",
    )

    # Lateral movement detection
    enable_lateral_detection: bool = Field(
        default=True,
        description="Detect and track lateral movement across nodes",
    )
    lateral_session_window_minutes: int = Field(
        default=30,
        description="Time window to consider for lateral movement correlation",
    )
