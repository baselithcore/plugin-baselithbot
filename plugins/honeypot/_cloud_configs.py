"""Cloud honeypot configuration models."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CloudAuthConfig(BaseModel):
    """Authentication configuration for cloud honeypot."""

    accept_any_signature: bool = Field(
        default=True,
        description="Accept any AWS signature for session tracking",
    )
    capture_credentials: bool = Field(
        default=True,
        description="Capture credentials from requests",
    )
    max_auth_failures: int = Field(
        default=5,
        description="Maximum authentication failures before blocking",
    )
    weak_keys_for_baiting: List[str] = Field(
        default_factory=list,
        description="Weak access keys to use as bait",
    )

    model_config = ConfigDict(extra="ignore")


class CloudResponseConfig(BaseModel):
    """Response configuration for cloud honeypot."""

    include_request_ids: bool = Field(
        default=True,
        description="Include AWS-style request IDs in responses",
    )
    simulate_latency_ms: int = Field(
        default=50,
        description="Simulated network latency in milliseconds",
    )
    error_message_verbosity: str = Field(
        default="detailed",
        description="Error message verbosity: minimal, standard, detailed",
    )

    model_config = ConfigDict(extra="ignore")


class CloudHoneypotConfig(BaseModel):
    """Cloud Management API specific configuration."""

    provider: str = Field(
        default="aws",
        description="Cloud provider to emulate: aws, azure, gcp",
    )
    region: str = Field(
        default="us-east-1",
        description="Simulated cloud region",
    )
    enabled_services: List[str] = Field(
        default_factory=lambda: ["iam", "s3", "sts"],
        description="Cloud services to simulate",
    )
    auth_config: Optional[CloudAuthConfig] = Field(
        default=None,
        description="Authentication configuration",
    )
    imds_enabled: bool = Field(
        default=True,
        description="Enable Instance Metadata Service (IMDS) simulation",
    )
    imds_version: str = Field(
        default="v1",
        description="IMDS version: v1 (vulnerable) or v2 (secure)",
    )
    response_config: Optional[CloudResponseConfig] = Field(
        default=None,
        description="Response generation configuration",
    )

    model_config = ConfigDict(extra="ignore")
