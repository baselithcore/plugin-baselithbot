"""Sequence feature extraction."""

import hashlib
from typing import List, Set

from ...models import AttackEvent
from .models import AttackFeatureVector
from .utils import normalize_command


def extract_sequence_features(
    features: AttackFeatureVector, events: List[AttackEvent]
) -> None:
    """Extract command/action sequence features."""
    commands: List[str] = []
    unique_cmds: Set[str] = set()

    for event in events:
        if event.command:
            cmd = normalize_command(event.command)
            commands.append(cmd)
            unique_cmds.add(cmd)

    features.command_count = len(commands)
    features.unique_commands = len(unique_cmds)

    if commands:
        # Average command length
        features.avg_command_length = sum(len(c) for c in commands) / len(commands)

        # Sequence hash (order-preserving)
        seq_repr = "|".join(commands[:20])  # First 20 commands
        features.command_sequence_hash = hashlib.md5(
            seq_repr.encode(), usedforsecurity=False
        ).hexdigest()
