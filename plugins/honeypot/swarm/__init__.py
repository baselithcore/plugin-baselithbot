"""Honeypot Swarm Package.

Provides swarm-based coordination for honeypot agents.

Modules:
- coordinator: Main HoneypotSwarmCoordinator class
- lifecycle: Lifecycle management mixin
- handlers: Handler loading and management mixin
- attack_processor: Attack event processing mixin
- response_generator: LLM response generation mixin
- stats: Statistics and query methods mixin
"""

from .coordinator import HoneypotSwarmCoordinator, PheromoneTypes

__all__ = [
    "HoneypotSwarmCoordinator",
    "PheromoneTypes",
]
