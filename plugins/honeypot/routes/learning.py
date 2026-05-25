"""Learning and feedback endpoints for Honeypot API.

Provides endpoints for submitting feedback and viewing learning statistics.
"""

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.post("/feedback/pattern")
async def submit_pattern_feedback(
    pattern_id: str,
    pattern_type: str,
    outcome: str,  # true_positive, false_positive, false_negative
    context: Optional[str] = None,
):
    """Submit feedback on a detected pattern."""
    from ..learning import HoneypotLearning

    learning = HoneypotLearning()
    await learning.initialize()

    feedback_id = await learning.record_pattern_feedback(
        pattern_id=pattern_id,
        pattern_type=pattern_type,
        outcome=outcome,
        source="api",
        context=context,
    )
    return {"feedback_id": feedback_id, "status": "recorded"}


@router.post("/feedback/response")
async def submit_response_feedback(
    response_id: str,
    command: str,
    engagement_seconds: float,
    led_to_more_commands: bool,
):
    """Submit feedback on response effectiveness."""
    from ..learning import HoneypotLearning

    learning = HoneypotLearning()
    await learning.initialize()

    feedback_id = await learning.record_response_feedback(
        response_id=response_id,
        command=command,
        engagement_seconds=engagement_seconds,
        led_to_more_commands=led_to_more_commands,
    )
    return {"feedback_id": feedback_id, "status": "recorded"}


@router.post("/feedback/session")
async def submit_session_feedback(
    session_id: str,
    duration_seconds: float,
    commands_count: int,
    captured_credentials: bool = False,
    outcome: str = "success",
):
    """Submit feedback on session success."""
    from ..learning import HoneypotLearning

    learning = HoneypotLearning()
    await learning.initialize()

    feedback_id = await learning.record_session_feedback(
        session_id=session_id,
        duration_seconds=duration_seconds,
        commands_count=commands_count,
        captured_credentials=captured_credentials,
        outcome=outcome,
    )
    return {"feedback_id": feedback_id, "status": "recorded"}


@router.get("/learning/stats")
async def get_learning_stats():
    """Get learning system statistics."""
    from ..learning import HoneypotLearning

    learning = HoneypotLearning()
    await learning.initialize()
    return learning.get_learning_stats()


@router.get("/learning/pattern-accuracy")
async def get_pattern_accuracy():
    """Get accuracy by pattern type."""
    from ..learning import HoneypotLearning

    learning = HoneypotLearning()
    await learning.initialize()
    return learning.get_pattern_accuracy()


@router.get("/learning/feedback-log")
async def get_feedback_log(limit: int = Query(50, ge=1, le=200)):
    """Get recent feedback entries."""
    from ..learning import HoneypotLearning

    learning = HoneypotLearning()
    await learning.initialize()
    return learning.get_feedback_log(limit=limit)


@router.post("/feedback/correlation")
async def submit_correlation_feedback(
    correlation_id: str,
    outcome: str,  # confirmed, rejected, false_positive
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Submit feedback on a CVE correlation.

    This feedback is used to improve correlation accuracy and is
    forwarded to CVE Hunter for learning.
    """
    if not coordinator:
        return {"error": "Coordinator not ready", "status": "failed"}

    # Access the correlator via coordinator
    correlator = coordinator._cve_correlator
    success = await correlator.record_feedback(
        correlation_id=correlation_id,
        outcome=outcome,
        source="api",
    )

    if success:
        return {
            "correlation_id": correlation_id,
            "outcome": outcome,
            "status": "recorded",
        }
    return {"error": "Correlation not found", "status": "failed"}


@router.get("/correlation/accuracy")
async def get_correlation_accuracy(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get CVE correlation accuracy statistics."""
    if not coordinator:
        return {"error": "Coordinator not ready"}

    correlator = coordinator._cve_correlator
    return correlator.get_accuracy_stats()
