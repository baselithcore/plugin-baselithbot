"""Discovery Data Models.

Pydantic models for botnet detection, network analysis, and discovery results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, ConfigDict, model_serializer

    PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel, Field

    PYDANTIC_V2 = False


def convert_numpy(value: Any) -> Any:
    """Convert numpy types to native Python types recursively.

    This function handles numpy scalars, arrays, and nested structures
    to ensure all values are JSON-serializable Python native types.
    """
    # Try to import numpy - if not available, just return value
    try:
        import numpy as np

        # Check for numpy scalar types explicitly
        if isinstance(value, (np.integer, np.floating, np.bool_)):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
    except ImportError:
        pass

    # Fallback: Handle any object with item() method (numpy scalars)
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    # Handle any object with tolist() method (numpy arrays)
    if hasattr(value, "tolist") and callable(getattr(value, "tolist")):
        try:
            return value.tolist()
        except (ValueError, TypeError):
            pass

    # Handle dicts recursively
    if isinstance(value, dict):
        return {convert_numpy(k): convert_numpy(v) for k, v in value.items()}

    # Handle lists/tuples recursively
    if isinstance(value, (list, tuple)):
        converted = [convert_numpy(v) for v in value]
        return converted if isinstance(value, list) else tuple(converted)

    # Handle Pydantic models
    if hasattr(value, "model_dump"):
        return convert_numpy(value.model_dump())
    elif hasattr(value, "dict"):
        return convert_numpy(value.model_dump())

    return value


class NumpySafeModel(BaseModel):
    """Base model with numpy serialization support.

    Uses both input validation and output serialization to ensure
    numpy types never cause serialization issues.
    """

    if PYDANTIC_V2:
        model_config = ConfigDict(
            # Allow arbitrary types during validation (we convert them)
            arbitrary_types_allowed=True,
        )

        @classmethod
        def model_validate(cls, obj, *args, **kwargs):
            """Override validation to convert numpy types before Pydantic processes them."""
            if isinstance(obj, dict):
                obj = convert_numpy(obj)
            return super().model_validate(obj, *args, **kwargs)

        @model_serializer(mode="wrap")
        def serialize_model(self, handler, info):
            """Custom serializer to handle numpy types during output."""
            # Get the default serialization result
            data = handler(self)
            # Recursively convert numpy types
            return convert_numpy(data)
    else:
        # Pydantic V1 Configuration
        class Config:
            arbitrary_types_allowed = True
            json_encoders = {
                # Add basic numpy support for V1 json encoding if needed
                # But our custom dict() override is better
            }

        def __init__(self, **data):
            # Pre-validate/convert numpy types
            data = convert_numpy(data)
            super().__init__(**data)

        def dict(self, *args, **kwargs):
            # Convert result of dict() to ensure clean native types
            d = super().dict(*args, **kwargs)
            return convert_numpy(d)

        def json(self, *args, **kwargs):
            # V1 json() uses dict() internally usually, or we can enforce it
            # But converting dict first is safer
            d = self.model_dump()
            from pydantic.json import pydantic_encoder
            import json

            return json.dumps(d, default=pydantic_encoder, **kwargs)


class BotnetCluster(NumpySafeModel):
    """Detected botnet community/cluster."""

    cluster_id: str = Field(..., description="Unique cluster identifier")
    member_ips: List[str] = Field(
        default_factory=list, description="IPs in this cluster"
    )
    suspected_cc_ip: Optional[str] = Field(
        default=None, description="Most likely C&C IP within cluster"
    )
    associated_cc_ips: List[str] = Field(
        default_factory=list, description="Associated C&C IPs (internal or external)"
    )
    associated_cc_metadata: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadata for associated C&Cs (e.g. connection strength)",
    )
    size: int = Field(default=0, description="Number of nodes in cluster")
    attack_coordination_score: float = Field(
        default=0.0, description="Score indicating coordinated behavior (0-1)"
    )
    common_protocols: List[str] = Field(
        default_factory=list, description="Protocols used by cluster members"
    )
    common_targets: List[str] = Field(
        default_factory=list, description="Common honeypot targets"
    )
    detection_confidence: float = Field(
        default=0.0, description="Confidence in botnet classification (0-1)"
    )
    first_detected: datetime = Field(
        default_factory=datetime.now, description="First detection time"
    )
    last_activity: datetime = Field(
        default_factory=datetime.now, description="Last activity time"
    )
    severity: str = Field(default="medium", description="Threat severity level")
    modularity_score: float = Field(
        default=0.0, description="Community modularity score"
    )


class HubNode(NumpySafeModel):
    """Potential C&C server based on graph centrality."""

    ip: str = Field(..., description="IP address of hub node")
    degree_centrality: float = Field(
        default=0.0, description="Degree centrality score (0-1)"
    )
    betweenness_centrality: float = Field(
        default=0.0, description="Betweenness centrality score (0-1)"
    )
    connected_bots: int = Field(default=0, description="Number of connected bot IPs")
    is_confirmed_cc: bool = Field(
        default=False, description="Whether confirmed as C&C server"
    )
    threat_score: float = Field(
        default=0.0, description="Combined threat score (0-100)"
    )
    cluster_id: Optional[str] = Field(
        default=None, description="Associated botnet cluster ID"
    )
    country_code: Optional[str] = Field(default=None, description="Country code")
    country: Optional[str] = Field(default=None, description="Country name")
    protocols: List[str] = Field(default_factory=list, description="Protocols used")
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)


class NetworkAnomaly(NumpySafeModel):
    """Detected network behavior anomaly."""

    anomaly_id: str = Field(..., description="Unique anomaly identifier")
    anomaly_type: str = Field(
        ..., description="Type: timing_sync, payload_similarity, geo_cluster, etc."
    )
    involved_ips: List[str] = Field(
        default_factory=list, description="IPs involved in anomaly"
    )
    description: str = Field(default="", description="Human-readable description")
    severity: str = Field(default="info", description="Severity level")
    confidence: float = Field(default=0.0, description="Detection confidence (0-1)")
    detected_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional anomaly metadata"
    )


class GraphNodeData(NumpySafeModel):
    """Node representation for frontend visualization."""

    id: str = Field(..., description="Node identifier (IP address)")
    type: str = Field(
        default="attacker", description="Node type: honeypot, attacker, cc"
    )
    cluster_id: Optional[str] = Field(default=None, description="Associated cluster")
    degree: int = Field(default=0, description="Node degree (connections)")
    centrality: float = Field(default=0.0, description="Centrality score")
    country_code: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    protocols: List[str] = Field(default_factory=list)
    severity: str = Field(default="info")
    attack_count: int = Field(default=0)
    is_hub: bool = Field(default=False, description="Whether node is a hub/C&C")
    is_confirmed_cc: bool = Field(default=False, description="Whether confirmed as C&C")


class GraphEdgeData(NumpySafeModel):
    """Edge representation for frontend visualization."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    weight: float = Field(default=1.0, description="Edge weight")
    is_intra_cluster: bool = Field(
        default=False, description="Whether edge is within same cluster"
    )


class DiscoveryGraphData(NumpySafeModel):
    """Complete graph data for visualization."""

    nodes: List[GraphNodeData] = Field(default_factory=list)
    edges: List[GraphEdgeData] = Field(default_factory=list)
    clusters: List[Dict[str, Any]] = Field(
        default_factory=list, description="Cluster metadata for coloring"
    )


class DiscoveryResult(NumpySafeModel):
    """Complete discovery analysis result."""

    analysis_id: str = Field(..., description="Unique analysis identifier")
    honeypot_id: Optional[str] = Field(
        default=None, description="Targeted honeypot (None = all)"
    )
    analyzed_at: datetime = Field(default_factory=datetime.now)
    total_nodes: int = Field(default=0, description="Total IPs analyzed")
    total_edges: int = Field(default=0, description="Total connections analyzed")
    botnets: List[BotnetCluster] = Field(
        default_factory=list, description="Detected botnet clusters"
    )
    hub_nodes: List[HubNode] = Field(
        default_factory=list, description="Potential C&C servers"
    )
    anomalies: List[NetworkAnomaly] = Field(
        default_factory=list, description="Detected anomalies"
    )
    graph_data: Optional[DiscoveryGraphData] = Field(
        default=None, description="Graph data for visualization"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Analysis summary stats"
    )
    suggestions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Suggested honeypots based on pattern analysis",
    )
