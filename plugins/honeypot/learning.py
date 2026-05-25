"""Honeypot Learning Integration.

Provides continuous learning using core.learning for:
- Feedback collection on attack detection accuracy
- Pattern effectiveness tracking
- Response strategy optimization
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from .config import HoneypotConfig

logger = get_logger(__name__)


class HoneypotLearning:
    """Learning system for honeypot improvement.

    Tracks:
    - Pattern detection accuracy (via user feedback)
    - Deception effectiveness (attacker engagement)
    - Response quality (session duration)
    """

    def __init__(self, config: Optional["HoneypotConfig"] = None):
        """Initialize learning system.

        Args:
            config: Honeypot configuration
        """
        self._config = config
        self._feedback_collector = None
        self._learner = None
        self._initialized = False

        # Local tracking before core learning is available
        self._feedback_log: List[Dict[str, Any]] = []
        self._pattern_stats: Dict[str, Dict[str, int]] = {}
        self._response_stats: Dict[str, Dict[str, float]] = {}

    @property
    def config(self) -> "HoneypotConfig":
        """Get config lazily."""
        if self._config is None:
            from .config import get_honeypot_config

            self._config = get_honeypot_config()
        return self._config

    async def initialize(self) -> bool:
        """Initialize learning components.

        Returns:
            True if successfully initialized
        """
        if self._initialized:
            return True

        try:
            from core.learning import FeedbackCollector, ContinuousLearner

            self._feedback_collector = FeedbackCollector()
            self._learner = ContinuousLearner()
            self._initialized = True
            logger.info("Honeypot learning system initialized")
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize learning: {e}")
            # Continue with local tracking
            return False

    # =========================================================================
    # Feedback Collection
    # =========================================================================

    async def record_pattern_feedback(
        self,
        pattern_id: str,
        pattern_type: str,
        outcome: str,  # "true_positive", "false_positive", "false_negative"
        source: str = "user",
        context: Optional[str] = None,
    ) -> str:
        """Record feedback on a detected pattern.

        Args:
            pattern_id: ID of the pattern
            pattern_type: Type of pattern (sql_injection, etc.)
            outcome: Feedback outcome
            source: Feedback source (user, automated)
            context: Additional context

        Returns:
            Feedback ID
        """
        feedback_id = f"fb-{uuid4().hex[:8]}"

        feedback = {
            "feedback_id": feedback_id,
            "pattern_id": pattern_id,
            "pattern_type": pattern_type,
            "outcome": outcome,
            "source": source,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._feedback_log.append(feedback)

        # Update pattern stats
        if pattern_type not in self._pattern_stats:
            self._pattern_stats[pattern_type] = {
                "true_positive": 0,
                "false_positive": 0,
                "false_negative": 0,
            }
        if outcome in self._pattern_stats[pattern_type]:
            self._pattern_stats[pattern_type][outcome] += 1

        # Record in core learning if available
        if self._feedback_collector:
            try:
                await self._feedback_collector.record(
                    action=f"pattern_detection:{pattern_type}",
                    success=outcome == "true_positive",
                    metadata=feedback,
                )
            except Exception as e:
                logger.warning(f"Failed to record feedback: {e}")

        logger.info(f"Recorded pattern feedback: {pattern_type} -> {outcome}")
        return feedback_id

    async def record_response_feedback(
        self,
        response_id: str,
        command: str,
        engagement_seconds: float,
        led_to_more_commands: bool,
    ) -> str:
        """Record feedback on a response's effectiveness.

        Args:
            response_id: Response ID
            command: Command that was responded to
            engagement_seconds: How long attacker stayed after response
            led_to_more_commands: Whether attacker issued more commands

        Returns:
            Feedback ID
        """
        feedback_id = f"rf-{uuid4().hex[:8]}"

        # Calculate reward
        reward = 0.0
        if led_to_more_commands:
            reward += 0.5
        reward += min(engagement_seconds / 60, 0.5)  # Up to 0.5 for 1 minute

        feedback = {
            "feedback_id": feedback_id,
            "response_id": response_id,
            "command": command,
            "engagement_seconds": engagement_seconds,
            "led_to_more_commands": led_to_more_commands,
            "reward": reward,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._feedback_log.append(feedback)

        # Update response stats
        if command not in self._response_stats:
            self._response_stats[command] = {
                "total_engagements": 0,
                "avg_engagement_seconds": 0,
                "continuation_rate": 0,
            }

        stats = self._response_stats[command]
        n = stats["total_engagements"]
        stats["avg_engagement_seconds"] = (
            stats["avg_engagement_seconds"] * n + engagement_seconds
        ) / (n + 1)
        stats["continuation_rate"] = (
            stats["continuation_rate"] * n + (1 if led_to_more_commands else 0)
        ) / (n + 1)
        stats["total_engagements"] = n + 1

        # Record in core learning
        if self._learner:
            try:
                await self._learner.record_experience(
                    state={"command": command},
                    action="generate_response",
                    reward=reward,
                    next_state={"engaged": led_to_more_commands},
                )
            except Exception as e:
                logger.warning(f"Failed to record experience: {e}")

        return feedback_id

    async def record_session_feedback(
        self,
        session_id: str,
        duration_seconds: float,
        commands_count: int,
        captured_credentials: bool,
        outcome: str,  # "success", "early_disconnect", "detected"
    ) -> str:
        """Record feedback on overall session success.

        Args:
            session_id: Session ID
            duration_seconds: Total session duration
            commands_count: Number of commands executed
            captured_credentials: Whether credentials were captured
            outcome: Session outcome

        Returns:
            Feedback ID
        """
        feedback_id = f"sf-{uuid4().hex[:8]}"

        # Calculate session score
        score = 0.0
        score += min(duration_seconds / 300, 0.3)  # Up to 0.3 for 5 minutes
        score += min(commands_count / 10, 0.3)  # Up to 0.3 for 10 commands
        if captured_credentials:
            score += 0.4
        if outcome == "success":
            score = min(score + 0.2, 1.0)

        feedback = {
            "feedback_id": feedback_id,
            "session_id": session_id,
            "duration_seconds": duration_seconds,
            "commands_count": commands_count,
            "captured_credentials": captured_credentials,
            "outcome": outcome,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._feedback_log.append(feedback)
        return feedback_id

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_pattern_accuracy(self) -> Dict[str, float]:
        """Get accuracy by pattern type.

        Returns:
            Dict of pattern_type -> accuracy (0-1)
        """
        result = {}
        for pattern_type, stats in self._pattern_stats.items():
            total = stats["true_positive"] + stats["false_positive"]
            if total > 0:
                result[pattern_type] = stats["true_positive"] / total
            else:
                result[pattern_type] = 0.0
        return result

    def get_response_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """Get response effectiveness stats.

        Returns:
            Dict of command -> effectiveness metrics
        """
        return self._response_stats.copy()

    def get_feedback_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent feedback entries.

        Args:
            limit: Maximum entries to return

        Returns:
            List of feedback entries
        """
        return self._feedback_log[-limit:]

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics."""
        return {
            "total_feedback": len(self._feedback_log),
            "tracked_patterns": len(self._pattern_stats),
            "tracked_responses": len(self._response_stats),
            "pattern_accuracy": self.get_pattern_accuracy(),
            "core_learning_enabled": self._initialized,
        }


async def initialize_learning(
    config: Optional["HoneypotConfig"] = None,
) -> HoneypotLearning:
    """Initialize and return HoneypotLearning instance."""
    learning = HoneypotLearning(config)
    await learning.initialize()
    return learning
