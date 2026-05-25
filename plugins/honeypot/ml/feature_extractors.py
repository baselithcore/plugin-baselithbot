"""Command and Category Feature Extraction.

Extracts command n-grams and category distribution features from
attack sessions for ML-based TTP prediction.
"""

import hashlib
from typing import List

from ..emulation.models import CommandRecord

# Command categories for feature encoding
COMMAND_CATEGORIES = {
    "filesystem": {"ls", "cat", "head", "tail", "find", "grep", "less", "more", "tree"},
    "navigation": {"cd", "pwd", "pushd", "popd"},
    "file_ops": {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "chmod", "chown"},
    "network": {
        "curl",
        "wget",
        "nc",
        "ncat",
        "ssh",
        "scp",
        "ping",
        "netstat",
        "ss",
        "ip",
        "ifconfig",
    },
    "process": {"ps", "top", "htop", "kill", "pkill", "pgrep", "jobs", "bg", "fg"},
    "system": {"uname", "hostname", "id", "whoami", "uptime", "w", "who", "last"},
    "user": {"useradd", "usermod", "userdel", "passwd", "su", "sudo"},
    "package": {"apt", "yum", "dnf", "pip", "npm", "gem"},
    "scripting": {"bash", "sh", "python", "perl", "ruby", "php", "awk", "sed"},
    "encoding": {"base64", "xxd", "od", "openssl"},
    "archive": {"tar", "zip", "unzip", "gzip", "gunzip", "bzip2"},
    "editor": {"vi", "vim", "nano", "emacs", "cat"},
}


def extract_command_ngrams(
    history: List[CommandRecord],
    ngram_size: int = 2,
) -> List[float]:
    """Extract command n-gram features using hashing.

    Uses feature hashing to map n-grams to fixed-size vector.

    Args:
        history: Command history
        ngram_size: Size of n-grams

    Returns:
        8 n-gram features
    """
    features = [0.0] * 8

    if len(history) < 2:
        return features

    # Extract command names only
    commands = [_extract_command_name(r.command) for r in history]

    # Build n-grams
    ngrams = []
    for i in range(len(commands) - ngram_size + 1):
        ngram = tuple(commands[i : i + ngram_size])
        ngrams.append(ngram)

    # Hash n-grams to feature indices
    for ngram in ngrams:
        ngram_str = "_".join(ngram)
        hash_val = int(
            hashlib.md5(ngram_str.encode(), usedforsecurity=False).hexdigest(), 16
        )
        idx = hash_val % 8
        features[idx] += 1.0

    # Normalize by count
    total = sum(features)
    if total > 0:
        features = [f / total for f in features]

    return features


def extract_command_categories(history: List[CommandRecord]) -> List[float]:
    """Extract command category distribution.

    Args:
        history: Command history

    Returns:
        12 category features (one per category)
    """
    category_counts = {cat: 0 for cat in COMMAND_CATEGORIES}
    total = 0

    for record in history:
        cmd_name = _extract_command_name(record.command)
        for cat, commands in COMMAND_CATEGORIES.items():
            if cmd_name in commands:
                category_counts[cat] += 1
                total += 1
                break

    # Convert to normalized features
    features = []
    for cat in sorted(COMMAND_CATEGORIES.keys()):
        if total > 0:
            features.append(category_counts[cat] / total)
        else:
            features.append(0.0)

    return features


def _extract_command_name(command: str) -> str:
    """Extract command name from full command string.

    Args:
        command: Full command string

    Returns:
        Base command name
    """
    parts = command.strip().split()
    if not parts:
        return ""

    cmd = parts[0]

    # Handle sudo
    if cmd == "sudo" and len(parts) > 1:
        cmd = parts[1]

    return cmd.lower()
