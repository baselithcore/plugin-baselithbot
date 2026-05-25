"""Unit Tests for n8n Handler (CVE-2026-21858).

Tests for the N8nHandler honeypot that detects Ni8mare exploitation attempts.
"""

import pytest
from unittest.mock import MagicMock
import re

from plugins.honeypot.custom_handlers.n8n_handler import (
    N8nHandler,
    N8N_EXPLOIT_PATTERNS,
    SCANNER_USER_AGENTS,
)
from plugins.honeypot.config import HoneypotConfig


class TestN8nExploitPatterns:
    """Test CVE-2026-21858 exploit pattern detection."""

    def test_filepath_injection_etc_passwd(self):
        """Test detection of /etc/passwd file read."""
        payload = '{"files": {"f-t8ebu1": {"filepath": "/etc/passwd"}}}'
        pattern = N8N_EXPLOIT_PATTERNS["passwd_read"]
        assert re.search(pattern, payload, re.IGNORECASE)

    def test_filepath_injection_etc_shadow(self):
        """Test detection of /etc/shadow file read."""
        payload = '{"files": {"f-abc": {"filepath": "/etc/shadow"}}}'
        pattern = N8N_EXPLOIT_PATTERNS["shadow_read"]
        assert re.search(pattern, payload, re.IGNORECASE)

    def test_filepath_injection_home_directory(self):
        """Test detection of home directory file read."""
        payload = '{"files": {"f-xyz": {"filepath": "/home/node/.n8n/config"}}}'
        pattern = N8N_EXPLOIT_PATTERNS["filepath_injection"]
        assert re.search(pattern, payload, re.IGNORECASE)

    def test_filepath_injection_var_directory(self):
        """Test detection of var directory file read."""
        payload = '{"files": {"f-xyz": {"filepath": "/var/log/auth.log"}}}'
        pattern = N8N_EXPLOIT_PATTERNS["filepath_injection"]
        assert re.search(pattern, payload, re.IGNORECASE)

    def test_database_read_sqlite(self):
        """Test detection of SQLite database read attempt."""
        payload = '{"files": {"f-db": {"filepath": "/home/node/.n8n/database.sqlite"}}}'
        pattern = N8N_EXPLOIT_PATTERNS["database_read"]
        assert re.search(pattern, payload, re.IGNORECASE)

    def test_config_read_n8n(self):
        """Test detection of n8n config read attempt."""
        payload = '{"files": {"f-cfg": {"filepath": "/home/node/.n8n/config"}}}'
        pattern = N8N_EXPLOIT_PATTERNS["config_read"]
        assert re.search(pattern, payload, re.IGNORECASE)

    def test_files_manipulation_structure(self):
        """Test detection of malicious files object structure."""
        payload = """{"data": {}, "files": {"f-t8ebu1": {"filepath": "/etc/passwd", "originalFilename": "z0nojfcn.bin"}}}"""
        pattern = N8N_EXPLOIT_PATTERNS["files_manipulation"]
        assert re.search(pattern, payload, re.IGNORECASE)

    def test_form_endpoint_pattern(self):
        """Test detection of vulnerable form endpoint path."""
        paths = ["/form/submit", "/form/test", "/form/upload", "/form/demo"]
        pattern = N8N_EXPLOIT_PATTERNS["json_to_form_endpoint"]
        for path in paths:
            assert re.search(pattern, path), f"Should match {path}"

    def test_webhook_endpoint_pattern(self):
        """Test detection of vulnerable webhook endpoint paths."""
        paths = ["/webhook/n8n", "/webhook/1", "/webhook-test/test"]
        pattern = N8N_EXPLOIT_PATTERNS["json_to_form_endpoint"]
        for path in paths:
            assert re.search(pattern, path), f"Should match {path}"

    def test_non_exploit_payload_not_matched(self):
        """Test that normal payloads don't trigger exploit patterns."""
        normal_payload = '{"data": {"name": "John", "email": "john@example.com"}}'
        for name, pattern in N8N_EXPLOIT_PATTERNS.items():
            if name != "json_to_form_endpoint":
                assert not re.search(pattern, normal_payload, re.IGNORECASE), (
                    f"Pattern {name} should not match normal payload"
                )


class TestScannerUserAgents:
    """Test scanner user-agent detection."""

    def test_python_requests_detected(self):
        """Test detection of python-requests user agent."""
        ua = "python-requests/2.32.5"
        assert any(re.search(p, ua) for p in SCANNER_USER_AGENTS)

    def test_curl_detected(self):
        """Test detection of curl user agent."""
        ua = "curl/8.0.1"
        assert any(re.search(p, ua) for p in SCANNER_USER_AGENTS)

    def test_go_http_client_detected(self):
        """Test detection of Go HTTP client user agent."""
        ua = "Go-http-client/1.1"
        assert any(re.search(p, ua) for p in SCANNER_USER_AGENTS)

    def test_normal_browser_not_detected(self):
        """Test that normal browser UAs don't trigger scanner detection."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        assert not any(re.search(p, ua) for p in SCANNER_USER_AGENTS)


class TestN8nHandlerInitialization:
    """Test N8nHandler class initialization."""

    @pytest.fixture
    def mock_config(self):
        """Create mock HoneypotConfig."""
        config = MagicMock(spec=HoneypotConfig)
        config.max_payload_size_kb = 64
        config.rate_limit_window_seconds = 60
        config.rate_limit_max_connections = 100
        return config

    def test_handler_initialization(self, mock_config):
        """Test handler initializes correctly."""
        handler = N8nHandler(config=mock_config, definition=None)

        assert handler._default_port == 5678
        assert handler._app is None
        assert handler._running is False

    def test_default_port(self, mock_config):
        """Test default n8n port is 5678."""
        handler = N8nHandler(config=mock_config, definition=None)
        assert handler._default_port == 5678


class TestN8nPayloadAnalysis:
    """Test payload analysis logic."""

    @pytest.fixture
    def handler(self):
        """Create handler for testing."""
        config = MagicMock(spec=HoneypotConfig)
        config.max_payload_size_kb = 64
        config.rate_limit_window_seconds = 60
        config.rate_limit_max_connections = 100
        return N8nHandler(config=config, definition=None)

    def test_full_ni8mare_exploit_detection(self, handler):
        """Test detection of complete Ni8mare exploit attempt."""
        body = '{"data": {}, "files": {"f-t8ebu1": {"filepath": "/etc/passwd", "originalFilename": "test.bin"}}}'
        path = "/form/submit"
        content_type = "application/json"
        method = "POST"

        detected, is_ni8mare = handler._analyze_n8n_payload(
            body, path, content_type, method
        )

        assert is_ni8mare is True
        assert "content_type_confusion" in detected
        assert "passwd_read" in detected or "filepath_injection" in detected

    def test_reconnaissance_only(self, handler):
        """Test detection of reconnaissance without exploit."""
        body = ""
        path = "/form/submit"
        content_type = "application/json"
        method = "POST"

        detected, is_ni8mare = handler._analyze_n8n_payload(
            body, path, content_type, method
        )

        assert is_ni8mare is False
        assert "content_type_confusion" in detected

    def test_normal_form_submission(self, handler):
        """Test that normal form submission is not flagged as exploit."""
        body = '{"name": "Test User", "email": "test@example.com"}'
        path = "/form/contact"
        content_type = "multipart/form-data"  # Normal content type
        method = "POST"

        detected, is_ni8mare = handler._analyze_n8n_payload(
            body, path, content_type, method
        )

        assert is_ni8mare is False
        # Should not detect content_type_confusion with multipart
        assert "content_type_confusion" not in detected


class TestN8nResponseGeneration:
    """Test response generation."""

    @pytest.fixture
    def handler(self):
        """Create handler for testing."""
        config = MagicMock(spec=HoneypotConfig)
        config.max_payload_size_kb = 64
        config.rate_limit_window_seconds = 60
        config.rate_limit_max_connections = 100
        handler = N8nHandler(config=config, definition=None)
        # Mock mask_response_headers to return input as-is
        handler.mask_response_headers = lambda h: h
        # Mock _get_n8n_response_headers to return headers without Content-Type
        handler._get_n8n_response_headers = lambda: {
            "X-n8n-Version": "1.120.0",
            "Access-Control-Allow-Origin": "*",
        }
        return handler

    def test_n8n_headers_contain_version(self, handler):
        """Test that n8n headers include version."""
        headers = handler._get_n8n_headers()
        assert headers["X-n8n-Version"] == "1.120.0"
        assert "application/json" in headers["Content-Type"]

    def test_exploit_response_returns_500(self, handler):
        """Test that exploit attempts get 500 response."""
        response = handler._generate_exploit_response("form", is_exploit=True)
        assert response.status == 500

    def test_normal_form_response_success(self, handler):
        """Test normal form response returns success."""
        response = handler._generate_exploit_response("form", is_exploit=False)
        assert response.status == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
