"""Countermeasures Module for Honeypot Plugin.

Implements countermeasure strategies per HoneyDOC Section IV-C2.
"""

from .dynamic_deployment import DynamicDeployer
from .flow_control import FlowController

__all__ = [
    "FlowController",
    "DynamicDeployer",
]
