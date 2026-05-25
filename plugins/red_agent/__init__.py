"""
Red Agent Plugin.

Autonomous Red Team agent: reconnaissance, DAST, SCA scanning with
sandbox-isolated execution and graph-based vulnerability mapping
backed by FalkorDB. Integrates with the auth plugin for RBAC and
applies SSRF/scope guardrails to every target.
"""

from plugins.red_agent.plugin import RedAgentPlugin

__all__ = ["RedAgentPlugin"]
__version__ = "0.1.0"
