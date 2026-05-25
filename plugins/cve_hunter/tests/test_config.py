"""Unit tests for CVE Hunter configuration helpers."""

import pytest
from pydantic import SecretStr

from plugins.cve_hunter.config import (
    CVEHunterConfig,
    get_cve_hunter_config,
    get_nvd_api_key,
    update_cve_hunter_config,
)


pytestmark = pytest.mark.unit


def test_default_config_is_a_singleton():
    a = get_cve_hunter_config()
    b = get_cve_hunter_config()
    assert a is b
    assert isinstance(a, CVEHunterConfig)


def test_enabled_sources_default_factory_returns_fresh_list():
    cfg1 = CVEHunterConfig()
    cfg2 = CVEHunterConfig()
    cfg1.enabled_sources.append("internal-test")
    # Mutating the first instance must NOT leak into a freshly created config.
    assert "internal-test" not in cfg2.enabled_sources


def test_nvd_api_key_is_secret_str():
    cfg = CVEHunterConfig(nvd_api_key="abc-123")
    # SecretStr does not leak when stringified.
    assert isinstance(cfg.nvd_api_key, SecretStr)
    assert "abc-123" not in repr(cfg.nvd_api_key)
    assert get_nvd_api_key(cfg) == "abc-123"


def test_get_nvd_api_key_handles_unset():
    cfg = CVEHunterConfig()
    assert get_nvd_api_key(cfg) is None


def test_update_cve_hunter_config_merges_overrides():
    overrides = {"scan_interval_minutes": 7, "enable_sast": True}
    cfg = update_cve_hunter_config(overrides)
    assert cfg.scan_interval_minutes == 7
    assert cfg.enable_sast is True
    # Singleton is mutated in place.
    assert get_cve_hunter_config() is cfg


def test_update_cve_hunter_config_with_empty_overrides_returns_singleton():
    initial = get_cve_hunter_config()
    cfg = update_cve_hunter_config({})
    assert cfg is initial
    cfg2 = update_cve_hunter_config(None)
    assert cfg2 is initial
