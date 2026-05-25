"""Anomaly detection logic for ML Analyzer."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .features import extract_features
from .utils import HAS_SKLEARN, IsolationForest, StandardScaler


def detect_anomalies_isolation_forest(
    events: List[AttackEvent],
    contamination: float = 0.1,
) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
    """Detect anomalous attack patterns using Isolation Forest.

    Args:
        events: Attack events to analyze
        contamination: Expected outlier fraction

    Returns:
        Tuple of (anomalies, metadata)
    """
    anomalies: List[NetworkAnomaly] = []

    if not HAS_SKLEARN or len(events) < 10:
        return anomalies, {"error": "Insufficient data or sklearn not available"}

    # Extract features
    features, ip_mapping = extract_features(events)

    if len(features) < 10:
        return anomalies, {"error": "Insufficient features"}

    # Normalize
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    # Run Isolation Forest
    iso_forest = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )
    predictions = iso_forest.fit_predict(scaled_features)
    scores = iso_forest.decision_function(scaled_features)

    # Find outliers
    outlier_ips = []
    for idx, pred in enumerate(predictions):
        if pred == -1:  # Outlier
            outlier_ips.append(
                {
                    "ip": ip_mapping[idx],
                    "anomaly_score": float(-scores[idx]),  # Higher = more anomalous
                }
            )

    # Sort by anomaly score
    outlier_ips.sort(key=lambda x: x["anomaly_score"], reverse=True)

    # Create anomalies for top outliers
    for outlier in outlier_ips[:10]:  # Top 10 outliers
        anomaly = NetworkAnomaly(
            anomaly_id=str(uuid.uuid4())[:8],
            anomaly_type="ml_outlier",
            involved_ips=[outlier["ip"]],
            description=(
                f"ML-detected outlier: IP {outlier['ip']} shows unusual behavior "
                f"(score: {outlier['anomaly_score']:.2f})"
            ),
            severity="high" if outlier["anomaly_score"] > 0.3 else "medium",
            confidence=min(1.0, outlier["anomaly_score"] * 2),
            detected_at=datetime.now(),
            metadata={
                "method": "Isolation Forest",
                "anomaly_score": outlier["anomaly_score"],
            },
        )
        anomalies.append(anomaly)

    return anomalies, {
        "total_samples": len(features),
        "outliers_detected": len(outlier_ips),
        "top_outlier_score": outlier_ips[0]["anomaly_score"] if outlier_ips else 0,
    }
