"""ExtractionMixin — feature extraction helper methods."""

import hashlib
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import List

import numpy as np

from ._constants import COMMAND_CATEGORIES, SUSPICIOUS_PATTERNS
from ...emulation.models import CommandRecord, CredentialAttempt, TimingStats


class ExtractionMixin:
    """Mixin providing individual feature extraction methods."""

    def _extract_command_ngrams(self, history: List[CommandRecord]) -> List[float]:
        """Extract command n-gram features using hashing.

        Uses feature hashing to map n-grams to fixed-size vector.

        Args:
            history: Command history

        Returns:
            8 n-gram features
        """
        features = [0.0] * 8

        if len(history) < 2:
            return features

        # Extract command names only
        commands = [self._extract_command_name(r.command) for r in history]

        # Build n-grams
        ngrams = []
        for i in range(len(commands) - self.ngram_size + 1):
            ngram = tuple(commands[i : i + self.ngram_size])
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

    def _extract_command_categories(self, history: List[CommandRecord]) -> List[float]:
        """Extract command category distribution.

        Args:
            history: Command history

        Returns:
            12 category features (one per category)
        """
        category_counts = {cat: 0 for cat in COMMAND_CATEGORIES}
        total = 0

        for record in history:
            cmd_name = self._extract_command_name(record.command)
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

    def _extract_timing_features(self, timing: TimingStats) -> List[float]:
        """Extract timing behavior features.

        Args:
            timing: Timing statistics

        Returns:
            6 timing features
        """
        features = []

        # Mean inter-command delay (normalized)
        mean_delay = timing.mean_inter_command_delay_ms
        normalized_mean = (mean_delay - self._timing_mean) / max(self._timing_std, 1.0)
        features.append(np.clip(normalized_mean, -3, 3))

        # Command rate (commands per minute)
        if timing.total_commands > 0:
            session_duration_min = max(
                (datetime.now(timezone.utc) - timing.session_start).total_seconds()
                / 60,
                0.1,
            )
            cmd_rate = timing.total_commands / session_duration_min
            features.append(np.clip(cmd_rate / 30.0, 0, 3))  # Normalized by 30 cpm
        else:
            features.append(0.0)

        # Delay variance indicator
        if timing.min_inter_command_delay_ms < float("inf"):
            delay_range = (
                timing.max_inter_command_delay_ms - timing.min_inter_command_delay_ms
            )
            normalized_range = delay_range / max(
                timing.mean_inter_command_delay_ms, 1.0
            )
            features.append(np.clip(normalized_range, 0, 5))
        else:
            features.append(0.0)

        # Is automated (very fast typing)
        features.append(1.0 if mean_delay < 200 else 0.0)

        # Is interactive (slow, variable timing)
        is_interactive = mean_delay > 1000 and timing.total_commands > 3
        features.append(1.0 if is_interactive else 0.0)

        # Typing speed estimate
        if timing.typing_speed_estimate_cpm:
            features.append(np.clip(timing.typing_speed_estimate_cpm / 300.0, 0, 2))
        else:
            features.append(0.5)  # Unknown

        return features

    def _extract_recon_features(self, history: List[CommandRecord]) -> List[float]:
        """Extract reconnaissance indicator features.

        Args:
            history: Command history

        Returns:
            5 reconnaissance features
        """
        features = []

        commands = [r.command for r in history]
        all_commands = " ".join(commands)

        # Directory traversal depth
        max_depth = 0
        for cmd in commands:
            if "../" in cmd:
                depth = cmd.count("../")
                max_depth = max(max_depth, depth)
        features.append(np.clip(max_depth / 5.0, 0, 1))

        # Sensitive file access count
        sensitive_paths = ["/etc/", "/root/", "/.ssh/", "/.aws/", "/var/log/"]
        sensitive_count = sum(
            1 for cmd in commands if any(p in cmd for p in sensitive_paths)
        )
        features.append(np.clip(sensitive_count / 10.0, 0, 1))

        # Suspicious pattern matches
        pattern_matches = sum(
            1 for pattern in SUSPICIOUS_PATTERNS if re.search(pattern, all_commands)
        )
        features.append(np.clip(pattern_matches / len(SUSPICIOUS_PATTERNS), 0, 1))

        # Environment/config enumeration
        env_commands = {"env", "set", "export", "printenv", "cat"}
        config_files = [".bashrc", ".profile", ".env", "config"]
        env_count = sum(
            1
            for cmd in commands
            if any(e in cmd for e in env_commands)
            or any(c in cmd for c in config_files)
        )
        features.append(np.clip(env_count / 5.0, 0, 1))

        # Network enumeration
        network_recon = {"netstat", "ss", "ip", "ifconfig", "route", "arp", "hostname"}
        network_count = sum(
            1 for cmd in commands if self._extract_command_name(cmd) in network_recon
        )
        features.append(np.clip(network_count / 5.0, 0, 1))

        return features

    def _extract_credential_features(
        self, attempts: List[CredentialAttempt]
    ) -> List[float]:
        """Extract credential attempt features.

        Args:
            attempts: List of credential attempts

        Returns:
            4 credential features
        """
        features = []

        if not attempts:
            return [0.0, 0.0, 0.0, 0.0]

        # Total attempts
        features.append(np.clip(len(attempts) / 20.0, 0, 1))

        # Unique usernames
        usernames = set(a.username for a in attempts)
        features.append(np.clip(len(usernames) / 10.0, 0, 1))

        # Unique passwords
        passwords = set(a.password for a in attempts)
        features.append(np.clip(len(passwords) / 20.0, 0, 1))

        # Average password entropy
        entropies = [self._calculate_entropy(a.password) for a in attempts]
        avg_entropy = sum(entropies) / len(entropies)
        features.append(np.clip(avg_entropy / 4.0, 0, 1))  # Normalized by 4 bits

        return features

    def _extract_payload_features(self, history: List[CommandRecord]) -> List[float]:
        """Extract payload complexity features.

        Args:
            history: Command history

        Returns:
            5 payload features
        """
        features = []

        if not history:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

        commands = [r.command for r in history]

        # Average command length
        avg_len = sum(len(cmd) for cmd in commands) / len(commands)
        features.append(np.clip(avg_len / 100.0, 0, 1))

        # Pipe usage frequency
        pipe_count = sum(cmd.count("|") for cmd in commands)
        features.append(np.clip(pipe_count / len(commands), 0, 1))

        # Redirection usage
        redirect_count = sum(
            1 for cmd in commands if ">" in cmd or ">>" in cmd or "<" in cmd
        )
        features.append(np.clip(redirect_count / len(commands), 0, 1))

        # Base64 or encoded content
        has_encoding = any("base64" in cmd or len(cmd) > 200 for cmd in commands)
        features.append(1.0 if has_encoding else 0.0)

        # Command chaining (;, &&, ||)
        chaining_count = sum(
            cmd.count(";") + cmd.count("&&") + cmd.count("||") for cmd in commands
        )
        features.append(np.clip(chaining_count / len(commands), 0, 1))

        return features

    def _extract_command_name(self, command: str) -> str:
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

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text.

        Args:
            text: Input text

        Returns:
            Entropy in bits
        """
        if not text:
            return 0.0

        counter = Counter(text)
        total = len(text)

        entropy = 0.0
        for count in counter.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log2(prob)

        return entropy
