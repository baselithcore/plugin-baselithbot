"""MCP and prompt injection endpoints for Honeypot API.

Provides endpoints for analyzing prompts for injection attacks.
"""

from typing import Optional

from fastapi import APIRouter, Depends

from core.auth import AuthRole
from plugins.auth.dependencies import require_roles

router = APIRouter(
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.USER))],
)


@router.post("/mcp/analyze")
async def analyze_prompt(
    prompt: str,
    session_id: Optional[str] = None,
    source: str = "api",
    honeypot_id: Optional[str] = None,
):
    """Analyze a prompt for injection attacks."""
    from ..engine.mcp_handler import create_llm_guard

    guard = create_llm_guard(honeypot_id=honeypot_id)
    result = await guard.analyze_prompt(
        prompt=prompt,
        session_id=session_id,
        source=source,
    )
    return result


@router.post("/mcp/check")
async def check_prompt_safety(prompt: str):
    """Quick check if prompt is safe (for pre-flight checks)."""
    from ..engine.mcp_handler import create_llm_guard

    guard = create_llm_guard()
    is_safe, reason = guard.check_prompt_safety(prompt)
    return {
        "is_safe": is_safe,
        "reason": reason,
    }


@router.get("/mcp/patterns")
async def get_injection_patterns():
    """Get list of detected injection pattern categories."""
    from ..engine.mcp_handler import INJECTION_PATTERNS

    return {
        "categories": list(INJECTION_PATTERNS.keys()),
        "total_patterns": sum(len(p) for p in INJECTION_PATTERNS.values()),
    }


@router.get("/mcp/stats")
async def get_mcp_stats():
    """Get MCP detection statistics."""
    from ..engine.mcp_handler import create_llm_guard

    guard = create_llm_guard()
    return guard.get_stats()
