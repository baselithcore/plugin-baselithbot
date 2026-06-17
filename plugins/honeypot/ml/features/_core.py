"""FeatureExtractor — core class."""

import math
from datetime import datetime, timezone
from typing import List, Optional

from core.observability.logging import get_logger
import numpy as np

from ...emulation.models import (
    CommandRecord,
    CredentialAttempt,
    SessionState,
    TimingStats,
)
from ._constants import COMMAND_CATEGORIES
from ._extraction import ExtractionMixin

logger = get_logger(__name__)


class FeatureExtractor(ExtractionMixin):
    """Extract ML features from attack sessions.

    Features are designed to capture attacker behavior patterns
    for TTP prediction using a Random Forest classifier.

    Feature Groups:
        1. Command N-grams (8 features)
        2. Command Categories (12 features)
        3. Timing Features (6 features)
        4. Reconnaissance Indicators (5 features)
        5. Credential Features (4 features)
        6. Payload Complexity (5 features)

    Total: 40 features
    """

    def __init__(self, ngram_size: int = 2, max_vocab_size: int = 100):
        """Initialize feature extractor.

        Args:
            ngram_size: Size of command n-grams
            max_vocab_size: Maximum vocabulary size for hashing
        """
        self.ngram_size = ngram_size
        self.max_vocab_size = max_vocab_size

        # Running statistics for normalization
        self._timing_mean = 1000.0  # Default 1 second
        self._timing_std = 500.0
        self._samples_seen = 0

    def extract(self, session: SessionState) -> np.ndarray:
        """Extract all features from a session.

        Args:
            session: Session state to extract features from

        Returns:
            Feature vector as numpy array (40 features)
        """
        features = []

        # 1. Command sequence features (8)
        features.extend(self._extract_command_ngrams(session.command_history))

        # 2. Command category features (12)
        features.extend(self._extract_command_categories(session.command_history))

        # 3. Timing features (6)
        features.extend(self._extract_timing_features(session.timing))

        # 4. Reconnaissance indicators (5)
        features.extend(self._extract_recon_features(session.command_history))

        # 5. Credential features (4)
        features.extend(self._extract_credential_features(session.auth_attempts))

        # 6. Payload complexity (5)
        features.extend(self._extract_payload_features(session.command_history))

        return np.array(features, dtype=np.float32)

    def extract_from_commands(
        self,
        command_history: List[str],
        timing_profile: Optional[TimingStats] = None,
        credentials_tried: Optional[List[CredentialAttempt]] = None,
    ) -> np.ndarray:
        """Extract features from raw command list.

        Convenience method for when full SessionState is not available.

        Args:
            command_history: List of command strings
            timing_profile: Optional timing statistics
            credentials_tried: Optional credential attempts

        Returns:
            Feature vector
        """
        # Convert strings to CommandRecords
        records = [
            CommandRecord(command=cmd, timestamp=datetime.now(timezone.utc))
            for cmd in command_history
        ]

        features = []

        features.extend(self._extract_command_ngrams(records))
        features.extend(self._extract_command_categories(records))

        if timing_profile:
            features.extend(self._extract_timing_features(timing_profile))
        else:
            features.extend([0.0] * 6)  # Placeholder timing features

        features.extend(self._extract_recon_features(records))
        features.extend(self._extract_credential_features(credentials_tried or []))
        features.extend(self._extract_payload_features(records))

        return np.array(features, dtype=np.float32)

    def update_stats(self, sessions: List[SessionState]) -> None:
        """Update running statistics from training data.

        Args:
            sessions: Training sessions
        """
        delays = []
        for session in sessions:
            if session.timing.mean_inter_command_delay_ms > 0:
                delays.append(session.timing.mean_inter_command_delay_ms)

        if delays:
            self._timing_mean = sum(delays) / len(delays)
            variance = sum((d - self._timing_mean) ** 2 for d in delays) / len(delays)
            self._timing_std = math.sqrt(variance)
            self._samples_seen += len(sessions)

    def get_feature_names(self) -> List[str]:
        """Get human-readable feature names.

        Returns:
            List of feature names
        """
        names = []

        # N-gram features
        for i in range(8):
            names.append(f"ngram_bucket_{i}")

        # Category features
        for cat in sorted(COMMAND_CATEGORIES.keys()):
            names.append(f"cat_{cat}")

        # Timing features
        names.extend(
            [
                "timing_mean_normalized",
                "timing_cmd_rate",
                "timing_variance",
                "timing_is_automated",
                "timing_is_interactive",
                "timing_speed_estimate",
            ]
        )

        # Recon features
        names.extend(
            [
                "recon_dir_traversal",
                "recon_sensitive_access",
                "recon_suspicious_patterns",
                "recon_env_enum",
                "recon_network_enum",
            ]
        )

        # Credential features
        names.extend(
            [
                "cred_total_attempts",
                "cred_unique_users",
                "cred_unique_passwords",
                "cred_password_entropy",
            ]
        )

        # Payload features
        names.extend(
            [
                "payload_avg_length",
                "payload_pipe_usage",
                "payload_redirect_usage",
                "payload_has_encoding",
                "payload_chaining",
            ]
        )

        return names
