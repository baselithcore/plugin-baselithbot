"""Unit tests for the dbview Node supervisor configuration + helpers.

These tests deliberately avoid spawning a real Node process — that path is
covered by end-to-end verification with ``node`` on PATH. The unit layer
focuses on:

* env-driven config composition (``build_supervisor_config``),
* runtime-prerequisite probing (``NodeSupervisor._ensure_runtime_available``),
* child-env assembly (prefix passthrough + supervisor-owned overrides),
* port allocation hygiene.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from plugins.dbview.supervisor import (
    NodeNotAvailableError,
    NodeSupervisor,
    SupervisorConfig,
    build_supervisor_config,
)
from plugins.dbview.supervisor.process import _allocate_port


def test_allocate_port_returns_usable_loopback_port():
    port = _allocate_port("127.0.0.1")
    assert 1024 < port < 65536, "ephemeral port must be in user range"


def test_build_supervisor_config_defaults_to_prod_and_loopback(tmp_path: Path):
    with patch.dict(os.environ, {}, clear=False):
        for var in (
            "DBVIEW_PLUGIN_MODE",
            "DBVIEW_INTERNAL_HOST",
            "DBVIEW_INTERNAL_PORT",
            "DBVIEW_STARTUP_TIMEOUT_S",
            "DBVIEW_HEALTH_INTERVAL_S",
            "DBVIEW_SHUTDOWN_GRACE_S",
            "DBVIEW_RESTART_MAX_ATTEMPTS",
        ):
            os.environ.pop(var, None)
        cfg = build_supervisor_config(tmp_path)
    assert cfg.mode == "prod"
    assert cfg.host == "127.0.0.1"
    assert cfg.port is None  # signals "allocate on start()"
    assert cfg.dbview_root == tmp_path / "dbview"
    assert cfg.startup_timeout_s == 90.0


def test_build_supervisor_config_honours_env_overrides(tmp_path: Path):
    env = {
        "DBVIEW_PLUGIN_MODE": "dev",
        "DBVIEW_INTERNAL_HOST": "0.0.0.0",
        "DBVIEW_INTERNAL_PORT": "55555",
        "DBVIEW_STARTUP_TIMEOUT_S": "10",
        "DBVIEW_RESTART_MAX_ATTEMPTS": "3",
    }
    with patch.dict(os.environ, env):
        cfg = build_supervisor_config(tmp_path)
    assert cfg.mode == "dev"
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 55555
    assert cfg.startup_timeout_s == 10.0
    assert cfg.restart_max_attempts == 3


def test_build_supervisor_config_rejects_invalid_mode(tmp_path: Path):
    with patch.dict(os.environ, {"DBVIEW_PLUGIN_MODE": "weird"}):
        cfg = build_supervisor_config(tmp_path)
    # Invalid values are warned + downgraded to prod, never propagated.
    assert cfg.mode == "prod"


def test_build_supervisor_config_yaml_overrides_beat_env(tmp_path: Path):
    with patch.dict(os.environ, {"DBVIEW_PLUGIN_MODE": "dev"}):
        cfg = build_supervisor_config(tmp_path, overrides={"mode": "prod", "port": 9001})
    assert cfg.mode == "prod"
    assert cfg.port == 9001


def test_ensure_runtime_available_raises_when_node_missing(tmp_path: Path):
    cfg = SupervisorConfig(plugin_dir=tmp_path, dbview_root=tmp_path / "dbview")
    sup = NodeSupervisor(cfg)
    with patch("plugins.dbview.supervisor.process.shutil.which", return_value=None):
        with pytest.raises(NodeNotAvailableError) as excinfo:
            sup._ensure_runtime_available()
    assert "Node.js" in str(excinfo.value)


def test_ensure_runtime_available_raises_when_pnpm_missing_in_dev(tmp_path: Path):
    cfg = SupervisorConfig(plugin_dir=tmp_path, dbview_root=tmp_path / "dbview", mode="dev")
    sup = NodeSupervisor(cfg)

    # ``node`` present, ``pnpm`` absent: dev mode must refuse to start.
    def side_effect(binary: str) -> str | None:
        return "/usr/bin/node" if binary == "node" else None

    with patch("plugins.dbview.supervisor.process.shutil.which", side_effect=side_effect):
        with pytest.raises(NodeNotAvailableError) as excinfo:
            sup._ensure_runtime_available()
    assert "pnpm" in str(excinfo.value)


def test_build_command_requires_built_dist_in_prod(tmp_path: Path):
    cfg = SupervisorConfig(plugin_dir=tmp_path, dbview_root=tmp_path / "dbview")
    sup = NodeSupervisor(cfg)
    with pytest.raises(FileNotFoundError) as excinfo:
        sup._build_command()
    assert "dist/main.js" in str(excinfo.value)
    assert "pnpm" in str(excinfo.value)  # actionable hint in the message


def test_build_command_uses_pnpm_dev_in_dev_mode(tmp_path: Path):
    cfg = SupervisorConfig(plugin_dir=tmp_path, dbview_root=tmp_path / "dbview", mode="dev")
    sup = NodeSupervisor(cfg)
    cmd = sup._build_command()
    assert cmd == ["pnpm", "dev"]


def test_build_env_passes_through_dbview_and_overrides_port(tmp_path: Path):
    env = {
        "DBVIEW_JWT_SECRET": "x" * 33,
        "DBVIEW_SECRET": "y" * 16,
        "OLLAMA_BASE_URL": "http://local:11434/api",
        "OPENAI_API_KEY": "sk-test",
        "UNRELATED_VAR": "should-not-pass",
    }
    cfg = SupervisorConfig(plugin_dir=tmp_path, dbview_root=tmp_path / "dbview")
    sup = NodeSupervisor(cfg)
    sup._port = 12345
    with patch.dict(os.environ, env, clear=False):
        out = sup._build_env()
    assert out["DBVIEW_JWT_SECRET"] == "x" * 33
    assert out["DBVIEW_SECRET"] == "y" * 16
    assert out["OLLAMA_BASE_URL"] == "http://local:11434/api"
    assert out["OPENAI_API_KEY"] == "sk-test"
    assert "UNRELATED_VAR" not in out
    # Supervisor-owned values override any inherited setting.
    assert out["PORT"] == "12345"
    assert out["NODE_ENV"] == "production"
    assert out.get("LOG_FORMAT") == "json"


def test_build_env_applies_extra_env_last(tmp_path: Path):
    # The plugin injects the gateway-auth contract via extra_env; it must win
    # over anything inherited from the host environment.
    cfg = SupervisorConfig(
        plugin_dir=tmp_path,
        dbview_root=tmp_path / "dbview",
        extra_env={"DBVIEW_GATEWAY_AUTH": "true", "DBVIEW_GATEWAY_SECRET": "z" * 32},
    )
    sup = NodeSupervisor(cfg)
    sup._port = 4242
    with patch.dict(os.environ, {"DBVIEW_GATEWAY_AUTH": "false"}, clear=False):
        out = sup._build_env()
    assert out["DBVIEW_GATEWAY_AUTH"] == "true"
    assert out["DBVIEW_GATEWAY_SECRET"] == "z" * 32
