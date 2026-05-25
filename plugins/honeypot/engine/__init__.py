"""Honeypot Engine Package.

Provides honeypot handlers for different protocols:
- SSH: Interactive shell emulation
- HTTP: Web application emulation
- TCP: Generic port listener (FTP, Telnet, Redis, etc.)
- MCP: LLM prompt injection detection
"""

from .tcp_handler import TCPHandler
from .mcp_handler import MCPHoneypot, create_llm_guard

__all__ = [
    "TCPHandler",
    "MCPHoneypot",
    "create_llm_guard",
]
