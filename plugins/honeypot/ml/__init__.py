"""Machine Learning Module for Advanced Deception System.

This module provides ML-powered predictive analytics for TTP prediction
and adaptive response generation.

Components:
    - TTPPredictor: Predicts attacker TTPs from session behavior
    - FeatureExtractor: Extracts ML features from attack sessions
    - AdaptiveResponseGenerator: Generates tailored bait content
    - TTPTrainingPipeline: Continuous model training

Usage:
    from plugins.honeypot.ml import (
        TTPPredictor,
        FeatureExtractor,
        AdaptiveResponseGenerator,
    )

    # Create predictor and get predictions
    predictor = TTPPredictor()
    predictions = await predictor.predict_next_ttp(session)
"""

from .features import FeatureExtractor
from .predictor import TTPPredictor
from .adaptive import AdaptiveResponseGenerator

__all__ = [
    "TTPPredictor",
    "FeatureExtractor",
    "AdaptiveResponseGenerator",
]


def get_training_pipeline():
    """Lazily import training pipeline to avoid heavy dependencies."""
    from .training import TTPTrainingPipeline

    return TTPTrainingPipeline
