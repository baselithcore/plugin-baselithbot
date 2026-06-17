"""StatefulEmulator core.

Maintains coherent session state across commands, integrates with the
fingerprint engine for consistent responses, and tracks mutations for
cluster synchronization.
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from ..command_parser import ParsedCommand
from ..fingerprint import FingerprintEngine
from ..latency import AdaptiveLatencyModeler, LatencyModeler
from ..models import (
    BaitContent,
    CommandRecord,
    EmulatedResponse,
    EnvMutation,
    FingerprintProfile,
    FSMutation,
    SessionState,
    TTPPrediction,
)
from ._windows_shim import WindowsShimMixin

if TYPE_CHECKING:
    from ...engine.vfs.core import VirtualFilesystem
    from ...engine.commands.processor import CommandProcessor

logger = get_logger(__name__)


class StatefulEmulator(WindowsShimMixin):
    """Stateful emulation engine for realistic deception.

    Maintains coherent session state across commands with:
    - Fingerprint-accurate responses
    - Realistic latency simulation
    - Mutation tracking for cluster sync
    - TTP detection and prediction hooks

    Example:
        >>> profile = FingerprintProfile.load("linux_ubuntu")
        >>> emulator = StatefulEmulator(session_id="abc123", fingerprint_profile=profile)
        >>> response = await emulator.process_command("ls -la")
    """

    def __init__(
        self,
        session_id: str,
        fingerprint_profile: Optional[FingerprintProfile] = None,
        session_state: Optional[SessionState] = None,
        enable_latency: bool = True,
        enable_adaptive_latency: bool = True,
        ttp_predictor: Optional[Any] = None,
        adaptive_generator: Optional[Any] = None,
    ):
        """Initialize stateful emulator.

        Args:
            session_id: Unique session identifier
            fingerprint_profile: OS fingerprint profile
            session_state: Existing session state (for cluster hydration)
            enable_latency: Whether to apply latency simulation
            enable_adaptive_latency: Whether to adapt latency to attacker speed
            ttp_predictor: Optional ML predictor for TTP prediction
            adaptive_generator: Optional adaptive response generator
        """
        self.session_id = session_id
        self.profile = fingerprint_profile or FingerprintProfile.get_default()

        # Initialize or restore session state
        if session_state:
            self.session = session_state
        else:
            # Check for Windows profile to set defaults
            is_windows = "windows" in self.profile.os_type

            if is_windows:
                user = "Administrator"
                # Use VFS-compatible internal path, map to Windows for display
                home = "/home/Administrator"
                display_home = r"C:\Users\Administrator"
                env_vars = {
                    "Path": r"C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0",
                    "USERNAME": user,
                    "USERPROFILE": display_home,
                    "OS": "Windows_NT",
                    "COMSPEC": r"C:\Windows\system32\cmd.exe",
                    "HOMEDRIVE": "C:",
                    "HOMEPATH": r"\Users\Administrator",
                }
                cwd = home
            else:
                user = "root"
                home = "/root"
                env_vars = None  # Use default from SessionState model
                cwd = "/root"

            self.session = SessionState(
                session_id=session_id,
                username=user,
                hostname=self._extract_hostname_from_profile(),
                home_dir=home,
                cwd=cwd,
                env_vars=env_vars
                if env_vars
                else SessionState(session_id="defaults").env_vars,
            )

        # Initialize engines
        self.fingerprint = FingerprintEngine(self.profile)

        if enable_adaptive_latency:
            self.latency = AdaptiveLatencyModeler(
                profile=self.profile,
                enabled=enable_latency,
            )
        else:
            self.latency = LatencyModeler(
                profile=self.profile,
                enabled=enable_latency,
            )

        # ML components (optional)
        self._ttp_predictor = ttp_predictor
        self._adaptive_generator = adaptive_generator

        # VFS and command processor (lazily initialized)
        self._vfs: Optional["VirtualFilesystem"] = None
        self._command_processor: Optional["CommandProcessor"] = None

        # Callback hooks
        self._on_ttp_detected: Optional[Callable] = None
        self._on_bait_triggered: Optional[Callable] = None
        self._on_mutation: Optional[Callable] = None

        # Track generated baits
        self._active_baits: Dict[str, BaitContent] = {}

        logger.debug(
            f"StatefulEmulator initialized: session={session_id}, profile={self.profile.profile_id}"
        )

    def _extract_hostname_from_profile(self) -> str:
        """Extract hostname from profile uname output."""
        uname = self.profile.uname_output
        parts = uname.split()
        if len(parts) >= 2:
            return parts[1]
        return "server"

    @property
    def vfs(self) -> "VirtualFilesystem":
        """Get or create virtual filesystem for session."""
        if self._vfs is None:
            from ...engine.vfs.core import VirtualFilesystem

            self._vfs = VirtualFilesystem(
                username=self.session.username,
                hostname=self.session.hostname,
            )
            # Set current directory from session
            if self.session.cwd != "/root":
                self._vfs.cd(self.session.cwd)
        return self._vfs

    @property
    def command_processor(self) -> "CommandProcessor":
        """Get or create command processor."""
        if self._command_processor is None:
            from ...engine.commands.processor import CommandProcessor

            self._command_processor = CommandProcessor(
                vfs=self.vfs,
                fingerprint=self._build_fingerprint_dict(),
            )
        return self._command_processor

    def _build_fingerprint_dict(self) -> Dict[str, Any]:
        """Build fingerprint dict for command processor."""
        return {
            "os_type": self.profile.os_type,
            "os_version": self.profile.os_version,
            "kernel": self.profile.kernel_version,
            "hostname": self.session.hostname,
            "username": self.session.username,
            "uname": self.profile.uname_output,
        }

    async def process_command(self, command: str) -> EmulatedResponse:
        """Process command with full state tracking.

        Args:
            command: Raw command string

        Returns:
            EmulatedResponse with output and metadata
        """
        timestamp = datetime.now(timezone.utc)

        # 1. Parse command with context awareness
        parsed = ParsedCommand(command)

        # 2. Check for bait triggers
        bait_triggered = await self._check_bait_triggers(parsed)

        # 3. Get TTP predictions if ML is enabled
        predictions = await self._get_ttp_predictions()

        # 4. Generate adaptive baits if predictions available
        if predictions and self._adaptive_generator:
            new_baits = await self._adaptive_generator.generate_bait(
                predictions, self.session
            )
            for bait in new_baits:
                self._inject_bait(bait)

        # 5. Apply mutations to VFS/env
        mutations = await self._compute_and_apply_mutations(parsed)

        # 6. Generate response
        output = ""
        handled = False

        # Windows Command Shim
        if "windows" in self.profile.os_type:
            output, handled = self._process_windows_command(command)

        if not handled:
            output = self.command_processor.process_command(command)

        # Sync session state with VFS (e.g. cwd updates)
        if self._vfs:
            self.session.cwd = self._vfs.pwd()

        # 7. Apply realistic latency
        latency_applied = await self.latency.simulate(parsed.operation_type)

        # Update adaptive latency tracker if available
        if (
            isinstance(self.latency, AdaptiveLatencyModeler)
            and self.session.command_history
        ):
            last_cmd = self.session.command_history[-1]
            delay_since_last = (timestamp - last_cmd.timestamp).total_seconds() * 1000
            self.latency.record_command_timing(delay_since_last)

        # 8. Record command in history
        record = CommandRecord(
            command=command,
            timestamp=timestamp,
            output_preview=output[:200] if output else None,
            exit_code=0,
            operation_type=parsed.operation_type,
            detected_ttp=parsed.detected_ttp,
        )
        self.session.add_command(record)

        # 9. Track TTP detection
        if parsed.detected_ttp:
            prediction = TTPPrediction(ttp=parsed.detected_ttp, confidence=1.0)
            self.session.detected_ttps.append(prediction)

            if self._on_ttp_detected:
                await self._on_ttp_detected(parsed.detected_ttp, self.session)

        # 10. Trigger mutation callbacks
        if mutations and self._on_mutation:
            for mutation in mutations:
                await self._on_mutation(mutation, self.session)

        return EmulatedResponse(
            output=output,
            exit_code=0,
            operation_type=parsed.operation_type,
            latency_applied_ms=latency_applied,
            mutations=mutations,
            detected_ttp=parsed.detected_ttp,
            bait_triggered=bait_triggered,
            alert_generated=bait_triggered
            and any(
                b.alert_priority in ("high", "critical")
                for b in self._active_baits.values()
            ),
        )

    async def _compute_and_apply_mutations(
        self, parsed: ParsedCommand
    ) -> List[FSMutation]:
        """Compute and apply state mutations from command.

        Args:
            parsed: Parsed command

        Returns:
            List of mutations applied
        """
        mutations = []
        now = datetime.now(timezone.utc)

        if parsed.creates_file and parsed.target_path:
            mutation_type = "create_dir" if parsed.command == "mkdir" else "create_file"
            mutation = FSMutation(
                mutation_type=mutation_type,
                path=parsed.target_path,
                timestamp=now,
            )
            self.session.apply_fs_mutation(mutation)
            mutations.append(mutation)

        if parsed.deletes_file and parsed.target_path:
            mutation = FSMutation(
                mutation_type="delete_file",
                path=parsed.target_path,
                timestamp=now,
            )
            self.session.apply_fs_mutation(mutation)
            mutations.append(mutation)

        if parsed.modifies_env and parsed.var_name:
            env_mutation = EnvMutation(
                var_name=parsed.var_name,
                var_value=parsed.var_value,
                action="set" if "=" in parsed.raw else "unset",
                timestamp=now,
            )
            self.session.apply_env_mutation(env_mutation)

        return mutations

    async def _get_ttp_predictions(self) -> List[TTPPrediction]:
        """Get TTP predictions from ML module.

        Returns:
            List of predicted TTPs
        """
        if not self._ttp_predictor:
            return []

        try:
            return await self._ttp_predictor.predict_next_ttp(self.session)
        except Exception as e:
            logger.warning(f"TTP prediction failed: {e}")
            return []

    async def _check_bait_triggers(self, parsed: ParsedCommand) -> bool:
        """Check if command triggers any baits.

        Args:
            parsed: Parsed command

        Returns:
            True if bait was triggered
        """
        triggered = False

        for path, bait in self._active_baits.items():
            if bait.trigger_on_access and path in parsed.raw:
                triggered = True

                if self._on_bait_triggered:
                    await self._on_bait_triggered(bait, parsed, self.session)

                if bait.external_webhook and bait.canary_token:
                    # Would trigger external webhook (not implemented here)
                    logger.warning(
                        f"Canary token triggered: path={path}, "
                        f"session={self.session_id}"
                    )

        return triggered

    def _inject_bait(self, bait: BaitContent) -> None:
        """Inject bait content into VFS.

        Args:
            bait: Bait content to inject
        """
        self._active_baits[bait.path] = bait

        # Create file in VFS
        self.vfs._create_file(
            path=bait.path,
            content=bait.content,
            permissions="rw-r--r--" if bait.path.startswith("/etc") else "rw-------",
        )

        logger.debug(f"Bait injected: path={bait.path}, priority={bait.alert_priority}")

    # ========== Callback Registration ==========

    def on_ttp_detected(self, callback: Callable) -> None:
        """Register callback for TTP detection.

        Args:
            callback: Async function(ttp, session)
        """
        self._on_ttp_detected = callback

    def on_bait_triggered(self, callback: Callable) -> None:
        """Register callback for bait triggers.

        Args:
            callback: Async function(bait, parsed, session)
        """
        self._on_bait_triggered = callback

    def on_mutation(self, callback: Callable) -> None:
        """Register callback for state mutations.

        Args:
            callback: Async function(mutation, session)
        """
        self._on_mutation = callback

    # ========== State Management ==========

    def get_state(self) -> SessionState:
        """Get current session state.

        Returns:
            Current SessionState
        """
        return self.session

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get serializable state snapshot for cluster sync.

        Returns:
            Dict suitable for JSON serialization
        """
        return self.session.model_dump()

    @classmethod
    def from_state(
        cls,
        state: SessionState,
        fingerprint_profile: Optional[FingerprintProfile] = None,
        **kwargs,
    ) -> "StatefulEmulator":
        """Create emulator from existing state.

        Used for cluster state hydration.

        Args:
            state: Existing session state
            fingerprint_profile: OS fingerprint profile
            **kwargs: Additional arguments for __init__

        Returns:
            StatefulEmulator with restored state
        """
        return cls(
            session_id=state.session_id,
            fingerprint_profile=fingerprint_profile,
            session_state=state,
            **kwargs,
        )

    def get_prompt(self) -> str:
        """Get current shell prompt.

        Returns:
            Shell prompt string
        """
        return self.session.get_prompt()
