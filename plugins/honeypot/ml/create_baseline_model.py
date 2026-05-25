"""Baseline TTP Model Generator.

Creates a simple fallback model for TTP prediction when no trained model exists.
This allows the ML module to be functional from day 1.
"""

from core.observability.logging import get_logger
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = get_logger(__name__)


def create_baseline_model(output_path: Path) -> RandomForestClassifier:
    """Create a simple baseline Random Forest for TTP prediction.

    This model provides basic predictions based on simple heuristics
    until real training data is available.

    Args:
        output_path: Path to save the model

    Returns:
        Trained baseline model
    """
    # Create synthetic training data with simple patterns
    # Feature vector: 40 features from FeatureExtractor
    # Labels: 20 TTPs from TTP enum

    n_samples = 200
    n_features = 40
    n_classes = 20

    # Generate synthetic data with simple patterns
    np.random.seed(42)
    X = np.random.randn(n_samples, n_features)

    # Create labels with some structure
    # Features 0-7: Command n-grams influence credential TTPs
    # Features 8-19: Command categories influence discovery TTPs
    # Features 20-25: Timing features influence automation detection
    y = np.zeros(n_samples, dtype=int)

    for i in range(n_samples):
        # Simple heuristic labeling
        if X[i, 20] > 0.5:  # Fast timing = automation
            y[i] = 5  # T1059 (Command Scripting)
        elif X[i, 22] > 0.5:  # Recon patterns
            y[i] = 2  # T1083 (File Discovery)
        elif X[i, 26] > 0.5:  # Credential patterns
            y[i] = 0  # T1003 (Credential Dumping)
        else:
            y[i] = np.random.randint(0, n_classes)

    # Train simple Random Forest
    model = RandomForestClassifier(
        n_estimators=50, max_depth=10, random_state=42, n_jobs=-1
    )

    model.fit(X, y)

    # Save model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)

    logger.info(f"Baseline model created and saved to {output_path}")
    logger.info(f"Model score on synthetic data: {model.score(X, y):.2%}")

    return model


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Default path
    default_path = (
        Path(__file__).parent.parent
        / "data"
        / "models"
        / "ttp_predictor_baseline.joblib"
    )

    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    print("Creating baseline TTP prediction model...")
    model = create_baseline_model(output_path)
    print(f"✅ Model created: {output_path}")
    print(f"   Classes: {len(model.classes_)}")
    print(f"   Features: {model.n_features_in_}")
