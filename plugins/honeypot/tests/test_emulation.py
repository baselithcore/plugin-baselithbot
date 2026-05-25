"""Unit tests for the Advanced Deception System - Emulation Module.

Tests cover:
- FingerprintProfile loading and validation
- FingerprintEngine header and fingerprint generation
- LatencyModeler delay calculation
- StatefulEmulator command processing and state tracking
- TTP detection from commands
"""

import asyncio
from datetime import datetime, timezone

import pytest

from plugins.honeypot.emulation.fingerprint import (
    FingerprintEngine,
    MultiProfileFingerprintEngine,
)
from plugins.honeypot.emulation.latency import AdaptiveLatencyModeler, LatencyModeler
from plugins.honeypot.emulation.command_parser import ParsedCommand
from plugins.honeypot.emulation.models import (
    CommandRecord,
    EnvMutation,
    FingerprintProfile,
    FSMutation,
    OperationType,
    SessionState,
    TTP,
)
from plugins.honeypot.emulation.stateful import StatefulEmulator


# =============================================================================
# FingerprintProfile Tests
# =============================================================================


class TestFingerprintProfile:
    """Tests for FingerprintProfile model."""

    def test_get_default_profile(self):
        """Test default profile creation."""
        profile = FingerprintProfile.get_default()

        assert profile.profile_id == "linux_ubuntu_default"
        assert profile.os_type == "linux_ubuntu"
        assert profile.tcp_ttl == 64
        assert "OpenSSH" in profile.ssh_banner

    def test_load_ubuntu_profile(self):
        """Test loading Ubuntu profile from YAML."""
        profile = FingerprintProfile.load("linux_ubuntu")

        assert "ubuntu" in profile.profile_id.lower()
        assert profile.os_type == "linux_ubuntu"
        assert profile.tcp_ttl == 64
        assert "OpenSSH" in profile.ssh_banner
        assert "Apache" in profile.http_server_header

    def test_load_centos_profile(self):
        """Test loading CentOS profile from YAML."""
        profile = FingerprintProfile.load("linux_centos")

        assert "centos" in profile.profile_id.lower()
        assert profile.os_type == "linux_centos"
        assert profile.tcp_ttl == 64

    def test_load_windows_profile(self):
        """Test loading Windows profile from YAML."""
        profile = FingerprintProfile.load("windows_server")

        assert "windows" in profile.profile_id.lower()
        assert profile.os_type == "windows_server"
        assert profile.tcp_ttl == 128  # Windows uses 128
        assert "IIS" in profile.http_server_header

    def test_load_nonexistent_profile_raises(self):
        """Test that loading nonexistent profile raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            FingerprintProfile.load("nonexistent_os")

    def test_latency_multipliers(self):
        """Test that latency multipliers are defined."""
        profile = FingerprintProfile.get_default()

        assert "filesystem_read" in profile.latency_multipliers
        assert "network_lookup" in profile.latency_multipliers
        assert profile.latency_multipliers["filesystem_read"] < 1.0
        assert profile.latency_multipliers["network_lookup"] > 1.0


# =============================================================================
# FingerprintEngine Tests
# =============================================================================


class TestFingerprintEngine:
    """Tests for FingerprintEngine."""

    @pytest.fixture
    def engine(self):
        """Create engine with default profile."""
        return FingerprintEngine(FingerprintProfile.get_default())

    def test_ssh_banner(self, engine):
        """Test SSH banner generation."""
        banner = engine.get_ssh_banner()

        assert banner.startswith("SSH-2.0-")
        assert "OpenSSH" in banner

    def test_http_headers(self, engine):
        """Test HTTP header generation."""
        headers = engine.generate_http_headers(
            content_type="text/html", content_length=1234
        )

        assert "Server" in headers
        assert "Content-Type" in headers
        assert headers["Content-Length"] == "1234"

    def test_http_header_ordering(self, engine):
        """Test that headers are ordered according to profile."""
        headers = engine.generate_http_headers()
        keys = list(headers.keys())

        # Date should typically come first for Apache
        if "Date" in keys:
            assert keys.index("Date") < keys.index("Server")

    def test_mask_response_headers(self, engine):
        """Test header masking removes Python indicators."""
        original = {
            "Server": "Python/3.10 aiohttp/3.8.1",
            "X-Python": "yes",
            "Content-Type": "text/html",
        }

        masked = engine.mask_response_headers(original)

        assert "X-Python" not in masked
        assert "Python" not in masked.get("Server", "")
        assert "Content-Type" in masked

    def test_tcp_options(self, engine):
        """Test TCP options generation."""
        options = engine.get_tcp_options()

        assert "ttl" in options
        assert "window_size" in options
        assert options["ttl"] == 64

    def test_uname_output(self, engine):
        """Test uname output generation."""
        uname = engine.get_uname_output()

        assert "Linux" in uname
        assert "x86_64" in uname

    def test_error_messages(self, engine):
        """Test OS-appropriate error messages."""
        perm = engine.get_error_message("permission_denied", "/etc/shadow")
        assert "Permission denied" in perm

        not_found = engine.get_error_message("not_found", "foo")
        assert "not found" in not_found


# =============================================================================
# LatencyModeler Tests
# =============================================================================


class TestLatencyModeler:
    """Tests for LatencyModeler."""

    @pytest.fixture
    def modeler(self):
        """Create disabled modeler for testing."""
        return LatencyModeler(FingerprintProfile.get_default(), enabled=False)

    def test_estimate_delay_filesystem(self, modeler):
        """Test filesystem read has low latency estimate."""
        delay = modeler.estimate_delay(OperationType.FILESYSTEM_READ)

        assert delay > 0
        assert delay < 50  # Should be relatively fast

    def test_estimate_delay_network(self, modeler):
        """Test network operation has higher latency estimate."""
        fs_delay = modeler.estimate_delay(OperationType.FILESYSTEM_READ)
        net_delay = modeler.estimate_delay(OperationType.NETWORK_LOOKUP)

        assert net_delay > fs_delay

    def test_estimate_delay_crypto(self, modeler):
        """Test crypto operation has highest latency estimate."""
        generic = modeler.estimate_delay(OperationType.GENERIC)
        crypto = modeler.estimate_delay(OperationType.CRYPTO_OP)

        assert crypto > generic

    def test_disabled_returns_zero(self, modeler):
        """Test disabled modeler returns 0 latency."""

        async def run():
            return await modeler.simulate(OperationType.GENERIC)

        latency = asyncio.get_event_loop().run_until_complete(run())
        assert latency == 0.0

    def test_with_multiplier(self, modeler):
        """Test multiplier affects estimates."""
        base = modeler.estimate_delay(OperationType.GENERIC)
        doubled = modeler.with_multiplier(2.0).estimate_delay(OperationType.GENERIC)

        assert doubled == pytest.approx(base * 2.0)

    def test_accepts_string_operation(self, modeler):
        """Test that string operation types are accepted."""
        delay = modeler.estimate_delay("filesystem_read")
        assert delay > 0


class TestAdaptiveLatencyModeler:
    """Tests for AdaptiveLatencyModeler."""

    def test_records_command_timing(self):
        """Test command timing recording."""
        modeler = AdaptiveLatencyModeler(enabled=False)

        modeler.record_command_timing(100)
        modeler.record_command_timing(200)
        modeler.record_command_timing(150)

        assert len(modeler._recent_command_times) == 3

    def test_adaptive_multiplier_for_fast_attacker(self):
        """Test adaptive multiplier increases for fast automated attacks."""
        modeler = AdaptiveLatencyModeler(enabled=False, adaptive_threshold_ms=500)

        # Simulate fast attacker (automated tool)
        for _ in range(5):
            modeler.record_command_timing(50)  # Very fast

        multiplier = modeler._get_adaptive_multiplier()
        assert multiplier > 1.0  # Should increase delays

    def test_adaptive_multiplier_for_slow_attacker(self):
        """Test adaptive multiplier stays 1.0 for slow manual attacks."""
        modeler = AdaptiveLatencyModeler(enabled=False, adaptive_threshold_ms=500)

        # Simulate slow attacker (manual)
        for _ in range(5):
            modeler.record_command_timing(2000)  # Slow typing

        multiplier = modeler._get_adaptive_multiplier()
        assert multiplier == 1.0


# =============================================================================
# ParsedCommand Tests
# =============================================================================


class TestParsedCommand:
    """Tests for ParsedCommand parsing."""

    def test_parse_simple_command(self):
        """Test parsing simple command."""
        cmd = ParsedCommand("ls")

        assert cmd.command == "ls"
        assert cmd.args == []
        assert cmd.operation_type == OperationType.FILESYSTEM_LIST

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        cmd = ParsedCommand("cat /etc/passwd")

        assert cmd.command == "cat"
        assert cmd.args == ["/etc/passwd"]
        assert cmd.operation_type == OperationType.FILESYSTEM_READ

    def test_detect_credential_access(self):
        """Test TTP detection for credential access."""
        cmd = ParsedCommand("cat /etc/shadow")

        assert cmd.detected_ttp == TTP.CREDENTIAL_DUMPING

    def test_detect_account_discovery(self):
        """Test TTP detection for account discovery."""
        cmd = ParsedCommand("whoami")

        assert cmd.detected_ttp == TTP.ACCOUNT_DISCOVERY

    def test_detect_system_discovery(self):
        """Test TTP detection for system discovery."""
        # Note: uname without os-release in command is detected via operation type,
        # but TTP is only set for specific patterns like cat /etc/os-release
        cmd = ParsedCommand("cat /etc/os-release")

        assert cmd.detected_ttp == TTP.SYSTEM_INFO_DISCOVERY

    def test_detect_file_creation(self):
        """Test file creation detection."""
        cmd = ParsedCommand("touch /tmp/test.txt")

        assert cmd.creates_file is True
        assert cmd.target_path == "/tmp/test.txt"  # nosec B108

    def test_detect_file_deletion(self):
        """Test file deletion detection."""
        cmd = ParsedCommand("rm /tmp/test.txt")

        assert cmd.deletes_file is True
        assert cmd.target_path == "/tmp/test.txt"  # nosec B108

    def test_detect_env_modification(self):
        """Test environment modification detection."""
        cmd = ParsedCommand("export PATH=/usr/bin")

        assert cmd.modifies_env is True
        assert cmd.var_name == "PATH"
        assert cmd.var_value == "/usr/bin"

    def test_detect_privilege_escalation(self):
        """Test TTP detection for privilege escalation."""
        # Note: when both sudo and /etc/shadow are present, credential dumping
        # takes precedence in the detection order
        cmd = ParsedCommand("sudo -l")  # List sudo privileges

        assert cmd.detected_ttp == TTP.SUDO_ABUSE

    def test_detect_network_operation(self):
        """Test network operation detection."""
        cmd = ParsedCommand("curl https://example.com")

        assert cmd.operation_type == OperationType.NETWORK_LOOKUP


# =============================================================================
# SessionState Tests
# =============================================================================


class TestSessionState:
    """Tests for SessionState model."""

    def test_create_session(self):
        """Test session creation with defaults."""
        session = SessionState(session_id="test-123")

        assert session.session_id == "test-123"
        assert session.username == "root"
        assert "PATH" in session.env_vars

    def test_add_command(self):
        """Test adding command to history."""
        session = SessionState(session_id="test")
        record = CommandRecord(command="ls", timestamp=datetime.now(timezone.utc))

        session.add_command(record)

        assert len(session.command_history) == 1
        assert session.command_history[0].command == "ls"

    def test_timing_update(self):
        """Test timing stats update."""
        session = SessionState(session_id="test")

        # Add commands with delays
        t1 = datetime.now(timezone.utc)
        session.add_command(CommandRecord(command="cmd1", timestamp=t1))

        # Add second command (timing.update will be called)
        from datetime import timedelta

        t2 = t1 + timedelta(milliseconds=500)
        session.add_command(CommandRecord(command="cmd2", timestamp=t2))

        assert session.timing.total_commands == 1  # Only inter-command delays counted

    def test_apply_fs_mutation(self):
        """Test filesystem mutation tracking."""
        session = SessionState(session_id="test")
        mutation = FSMutation(mutation_type="create_file", path="/tmp/test.txt")  # nosec B108

        session.apply_fs_mutation(mutation)

        assert len(session.fs_mutations) == 1

    def test_apply_env_mutation(self):
        """Test environment mutation."""
        session = SessionState(session_id="test")
        mutation = EnvMutation(var_name="TEST", var_value="hello", action="set")

        session.apply_env_mutation(mutation)

        assert session.env_vars["TEST"] == "hello"

    def test_get_prompt(self):
        """Test shell prompt generation."""
        session = SessionState(
            session_id="test", username="root", hostname="server", cwd="/root"
        )

        prompt = session.get_prompt()

        assert "root@server" in prompt
        assert "#" in prompt  # Root prompt


# =============================================================================
# StatefulEmulator Tests
# =============================================================================


class TestStatefulEmulator:
    """Tests for StatefulEmulator."""

    @pytest.fixture
    def emulator(self):
        """Create emulator with latency disabled."""
        profile = FingerprintProfile.get_default()
        return StatefulEmulator(
            session_id="test-emulator",
            fingerprint_profile=profile,
            enable_latency=False,
        )

    @pytest.mark.asyncio
    async def test_process_command(self, emulator):
        """Test basic command processing."""
        response = await emulator.process_command("whoami")

        assert response.exit_code == 0
        assert response.operation_type == OperationType.SYSTEM_INFO
        assert response.detected_ttp == TTP.ACCOUNT_DISCOVERY

    @pytest.mark.asyncio
    async def test_command_history(self, emulator):
        """Test command history tracking."""
        await emulator.process_command("ls")
        await emulator.process_command("pwd")
        await emulator.process_command("whoami")

        assert len(emulator.session.command_history) == 3

    @pytest.mark.asyncio
    async def test_ttp_detection_tracking(self, emulator):
        """Test TTP detection is tracked in session."""
        await emulator.process_command("whoami")
        await emulator.process_command("cat /etc/passwd")

        ttps = [p.ttp for p in emulator.session.detected_ttps]
        assert TTP.ACCOUNT_DISCOVERY in ttps

    @pytest.mark.asyncio
    async def test_env_mutation(self, emulator):
        """Test environment mutation from export command."""
        await emulator.process_command("export MYVAR=test123")

        assert "MYVAR" in emulator.session.env_vars
        assert emulator.session.env_vars["MYVAR"] == "test123"

    def test_get_prompt(self, emulator):
        """Test prompt generation."""
        prompt = emulator.get_prompt()

        assert "root" in prompt
        assert "#" in prompt

    def test_get_state_snapshot(self, emulator):
        """Test state serialization."""
        snapshot = emulator.get_state_snapshot()

        assert "session_id" in snapshot
        assert "command_history" in snapshot
        assert snapshot["session_id"] == "test-emulator"

    def test_from_state_restoration(self, emulator):
        """Test emulator creation from existing state."""
        state = SessionState(
            session_id="restored-session", username="admin", cwd="/home/admin"
        )

        new_emulator = StatefulEmulator.from_state(state, enable_latency=False)

        assert new_emulator.session_id == "restored-session"
        assert new_emulator.session.username == "admin"

    @pytest.mark.asyncio
    async def test_callback_on_ttp_detected(self, emulator):
        """Test TTP detection callback is called."""
        detected_ttps = []

        async def capture_ttp(ttp, session):
            detected_ttps.append(ttp)

        emulator.on_ttp_detected(capture_ttp)
        await emulator.process_command("cat /etc/shadow")

        assert TTP.CREDENTIAL_DUMPING in detected_ttps


# =============================================================================
# MultiProfileFingerprintEngine Tests
# =============================================================================


class TestMultiProfileFingerprintEngine:
    """Tests for MultiProfileFingerprintEngine."""

    def test_register_profile(self):
        """Test profile registration."""
        engine = MultiProfileFingerprintEngine()
        profile = FingerprintProfile.get_default()

        engine.register_profile(profile, set_default=True)

        assert profile.profile_id in engine.list_profiles()

    def test_get_engine_for_profile(self):
        """Test getting engine for specific profile."""
        multi = MultiProfileFingerprintEngine()
        ubuntu = FingerprintProfile.load("linux_ubuntu")

        multi.register_profile(ubuntu)
        engine = multi.get_engine(ubuntu.profile_id)

        assert engine.profile.profile_id == ubuntu.profile_id

    def test_get_default_engine(self):
        """Test getting default engine."""
        multi = MultiProfileFingerprintEngine()
        ubuntu = FingerprintProfile.load("linux_ubuntu")

        multi.register_profile(ubuntu, set_default=True)
        engine = multi.get_engine()  # No specific ID

        assert engine.profile.profile_id == ubuntu.profile_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
