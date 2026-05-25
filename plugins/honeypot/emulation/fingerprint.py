"""Fingerprint Engine for Sophisticated Emulation.

Generates consistent, OS-accurate fingerprints across protocols to
defeat fingerprint-based honeypot detection tools like p0f, nmap, etc.

Supports:
- TCP/IP stack fingerprinting (TTL, window size, options)
- SSH fingerprinting (banner, algorithms)
- HTTP fingerprinting (headers, ordering, casing)
- TLS/JA4 fingerprinting (extends existing ja4_fingerprinter)
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import FingerprintProfile

logger = get_logger(__name__)


class FingerprintEngine:
    """Generates consistent fingerprints for honeypot emulation.

    Ensures that all protocol-level responses match the expected
    fingerprint profile of the emulated operating system.

    Example:
        >>> engine = FingerprintEngine(FingerprintProfile.load("linux_ubuntu"))
        >>> headers = engine.generate_http_headers(content_type="text/html")
        >>> ssh_banner = engine.get_ssh_banner()
    """

    def __init__(self, profile: Optional[FingerprintProfile] = None):
        """Initialize fingerprint engine.

        Args:
            profile: OS fingerprint profile to use
        """
        self.profile = profile or FingerprintProfile.get_default()
        logger.debug(
            f"FingerprintEngine initialized: profile={self.profile.profile_id}"
        )

    # ========== SSH Fingerprinting ==========

    def get_ssh_banner(self) -> str:
        """Get SSH server banner matching profile.

        Returns:
            SSH-2.0 compatible banner string
        """
        return f"SSH-2.0-{self.profile.ssh_banner}"

    def get_ssh_kex_algorithms(self) -> List[str]:
        """Get SSH key exchange algorithms for profile.

        Returns:
            List of KEX algorithm names
        """
        return self.profile.ssh_kex_algorithms.copy()

    def get_ssh_ciphers(self) -> List[str]:
        """Get SSH cipher algorithms for profile.

        Returns:
            List of cipher names
        """
        return self.profile.ssh_ciphers.copy()

    def get_ssh_motd(self) -> str:
        """Get SSH message of the day.

        Returns:
            MOTD string
        """
        return self.profile.motd_banner

    # ========== HTTP Fingerprinting ==========

    def generate_http_headers(
        self,
        content_type: str = "text/html; charset=utf-8",
        content_length: Optional[int] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Generate HTTP response headers matching profile.

        Headers are ordered according to the profile's specification
        to match the expected fingerprint of the emulated server.

        Args:
            content_type: Content-Type header value
            content_length: Content-Length (if known)
            extra_headers: Additional headers to include

        Returns:
            Ordered dict of HTTP headers
        """
        # Build headers in profile-specified order
        headers = {}

        for header_name in self.profile.http_header_order:
            value = self._get_standard_header_value(
                header_name, content_type, content_length
            )
            if value is not None:
                headers[self._apply_header_casing(header_name)] = value

        # Add extra headers
        if extra_headers:
            for name, value in extra_headers.items():
                headers[self._apply_header_casing(name)] = value

        return headers

    def _get_standard_header_value(
        self,
        header_name: str,
        content_type: str,
        content_length: Optional[int],
    ) -> Optional[str]:
        """Get value for standard HTTP header.

        Args:
            header_name: Header name
            content_type: Content type for response
            content_length: Content length (if known)

        Returns:
            Header value or None to skip
        """
        header_lower = header_name.lower()

        if header_lower == "date":
            return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        elif header_lower == "server":
            return self.profile.http_server_header
        elif header_lower == "content-type":
            return content_type
        elif header_lower == "content-length" and content_length is not None:
            return str(content_length)
        elif header_lower == "x-powered-by":
            # Only include if it's in the profile (some servers don't have this)
            if "PHP" in self.profile.http_server_header:
                return "PHP/8.2.0"
            return None
        elif header_lower == "connection":
            return "keep-alive"

        return None

    def _apply_header_casing(self, header_name: str) -> str:
        """Apply header casing according to profile.

        Args:
            header_name: Original header name

        Returns:
            Header name with proper casing
        """
        casing = self.profile.http_header_casing

        if casing == "lower":
            return header_name.lower()
        elif casing == "title":
            return "-".join(word.capitalize() for word in header_name.split("-"))
        else:  # "original"
            return header_name

    def mask_response_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask/replace headers that reveal honeypot nature.

        Per HoneyDOC stealth design: Hide Python-specific headers
        and replace with profile-consistent values.

        Args:
            headers: Original response headers

        Returns:
            Masked headers
        """
        masked = {}

        for name, value in headers.items():
            name_lower = name.lower()

            # Replace server headers
            if name_lower == "server":
                masked[self._apply_header_casing("Server")] = (
                    self.profile.http_server_header
                )
            # Remove Python/asyncio indicators
            elif name_lower in ("x-python", "x-asyncio", "x-fastapi"):
                continue
            # Keep other headers
            else:
                masked[self._apply_header_casing(name)] = value

        return masked

    # ========== TCP/IP Fingerprinting ==========

    def get_tcp_options(self) -> Dict[str, Any]:
        """Get TCP socket options matching profile.

        These should be applied to sockets to match the OS fingerprint.

        Returns:
            Dict of socket options
        """
        return {
            "ttl": self.profile.tcp_ttl,
            "window_size": self.profile.tcp_window_size,
            "options": self.profile.tcp_options,
            "df_flag": self.profile.tcp_df_flag,
            "window_scale": self.profile.tcp_window_scale,
        }

    def get_ttl(self) -> int:
        """Get IP TTL for profile.

        Returns:
            TTL value (typically 64 for Linux, 128 for Windows)
        """
        return self.profile.tcp_ttl

    # ========== System Info Fingerprinting ==========

    def get_uname_output(self) -> str:
        """Get uname -a output for profile.

        Returns:
            Simulated uname output
        """
        return self.profile.uname_output

    def get_os_release(self) -> Dict[str, str]:
        """Generate /etc/os-release content for profile.

        Returns:
            Dict suitable for generating os-release file
        """
        os_type = self.profile.os_type
        version = self.profile.os_version

        if os_type == "linux_ubuntu":
            return {
                "NAME": "Ubuntu",
                "VERSION": version,
                "ID": "ubuntu",
                "ID_LIKE": "debian",
                "PRETTY_NAME": f"Ubuntu {version}",
                "VERSION_ID": version.split()[0] if version else "22.04",
                "HOME_URL": "https://www.ubuntu.com/",
                "SUPPORT_URL": "https://help.ubuntu.com/",
                "BUG_REPORT_URL": "https://bugs.launchpad.net/ubuntu/",
            }
        elif os_type == "linux_centos":
            return {
                "NAME": "CentOS Stream",
                "VERSION": version,
                "ID": "centos",
                "ID_LIKE": "rhel fedora",
                "PRETTY_NAME": f"CentOS Stream {version}",
                "VERSION_ID": version.split()[0] if version else "9",
                "HOME_URL": "https://centos.org/",
            }
        elif os_type == "linux_debian":
            return {
                "NAME": "Debian GNU/Linux",
                "VERSION": version,
                "ID": "debian",
                "PRETTY_NAME": f"Debian GNU/Linux {version}",
                "VERSION_ID": version.split()[0] if version else "12",
                "HOME_URL": "https://www.debian.org/",
            }
        else:
            # Generic Linux
            return {
                "NAME": "Linux",
                "VERSION": version,
                "ID": "linux",
                "PRETTY_NAME": f"Linux {version}",
            }

    def get_kernel_info(self) -> Dict[str, str]:
        """Get kernel information for profile.

        Returns:
            Dict with kernel version info
        """
        return {
            "version": self.profile.kernel_version or "5.15.0-88-generic",
            "architecture": self.profile.architecture,
            "hostname": "ubuntu-server",  # Default, overridden by session
        }

    def format_os_release(self) -> str:
        """Format /etc/os-release file content.

        Returns:
            File content as string
        """
        release = self.get_os_release()
        lines = [f'{key}="{value}"' for key, value in release.items()]
        return "\n".join(lines) + "\n"

    # ========== Error Response Generation ==========

    def get_error_message(self, error_type: str, context: str = "") -> str:
        """Get OS-appropriate error message.

        Args:
            error_type: Type of error (permission, not_found, etc.)
            context: Context for the error (file path, etc.)

        Returns:
            Error message string
        """
        os_type = self.profile.os_type

        if error_type == "permission_denied":
            if "windows" in os_type:
                return "Access is denied."
            return f"-bash: {context}: Permission denied"

        elif error_type == "not_found":
            if "windows" in os_type:
                return (
                    f"'{context}' is not recognized as an internal or external command"
                )
            return f"-bash: {context}: command not found"

        elif error_type == "no_such_file":
            if "windows" in os_type:
                return "The system cannot find the file specified."
            return f"cat: {context}: No such file or directory"

        elif error_type == "is_directory":
            return f"cat: {context}: Is a directory"

        return f"Error: {error_type}"

    # ========== Profile Management ==========

    def with_profile(self, profile: FingerprintProfile) -> "FingerprintEngine":
        """Create new engine with different profile.

        Args:
            profile: New fingerprint profile

        Returns:
            New FingerprintEngine instance
        """
        return FingerprintEngine(profile=profile)

    def get_profile_summary(self) -> Dict[str, Any]:
        """Get summary of current profile for debugging.

        Returns:
            Dict with profile summary
        """
        return {
            "profile_id": self.profile.profile_id,
            "os_type": self.profile.os_type,
            "os_version": self.profile.os_version,
            "ssh_banner": self.profile.ssh_banner,
            "http_server": self.profile.http_server_header,
            "tcp_ttl": self.profile.tcp_ttl,
        }


class MultiProfileFingerprintEngine:
    """Manages multiple fingerprint profiles for dynamic switching.

    Useful for honeypots that emulate different systems based on
    the attack context or for A/B testing profile effectiveness.
    """

    def __init__(self):
        """Initialize multi-profile engine."""
        self._profiles: Dict[str, FingerprintProfile] = {}
        self._engines: Dict[str, FingerprintEngine] = {}
        self._default_profile_id: Optional[str] = None

    def register_profile(
        self, profile: FingerprintProfile, set_default: bool = False
    ) -> None:
        """Register a fingerprint profile.

        Args:
            profile: Profile to register
            set_default: Whether to set as default profile
        """
        self._profiles[profile.profile_id] = profile
        self._engines[profile.profile_id] = FingerprintEngine(profile)

        if set_default or self._default_profile_id is None:
            self._default_profile_id = profile.profile_id

    def get_engine(self, profile_id: Optional[str] = None) -> FingerprintEngine:
        """Get engine for profile.

        Args:
            profile_id: Profile ID or None for default

        Returns:
            FingerprintEngine for profile
        """
        pid = profile_id or self._default_profile_id
        if pid is None:
            raise ValueError("No profiles registered")

        if pid not in self._engines:
            raise KeyError(f"Profile not found: {pid}")

        return self._engines[pid]

    def list_profiles(self) -> List[str]:
        """List registered profile IDs.

        Returns:
            List of profile IDs
        """
        return list(self._profiles.keys())
