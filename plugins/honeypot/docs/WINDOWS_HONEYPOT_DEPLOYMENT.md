"""
Windows Server SSH Honeypot Configuration

Deploy a dedicated honeypot instance that emulates Windows Server 2022.
This configuration can be used standalone or in conjunction with Linux honeypots.
"""

# Environment variables for Windows Server Honeypot

HONEYPOT_WINDOWS_CONFIG = """

# Windows Server Honeypot Instance

HONEYPOT_EMULATION_ENABLED=true
HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=windows_server  # Key difference!
HONEYPOT_EMULATION_FINGERPRINT_STRICTNESS=high
HONEYPOT_EMULATION_ENABLE_LATENCY_SIMULATION=true

# Use same ML and Cluster settings

HONEYPOT_ML_ENABLED=true
HONEYPOT_ML_MODEL_PATH=data/models/ttp_predictor_baseline.joblib

HONEYPOT_CLUSTER_ENABLED=true
HONEYPOT_CLUSTER_REDIS_URL=redis://falkordb:6379/0

# Windows-specific SSH configuration

HONEYPOT_SSH_PORT=3390  # Different port for Windows instance
HONEYPOT_SSH_SERVER_NAME=WIN-SRV-2022-PROD
HONEYPOT_SSH_BANNER=SSH-2.0-OpenSSH_for_Windows_8.1
"""

# Docker Compose example for multi-OS deployment

DOCKER_COMPOSE_MULTI_OS = """
version: '3.8'

services:

# Linux Ubuntu Honeypot (default)

  honeypot-linux:
    image: your-honeypot-image
    environment:
      - HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=linux_ubuntu
      - HONEYPOT_SSH_PORT=2222
      - HONEYPOT_SSH_SERVER_NAME=ubuntu-server
    ports:
      - "2222:2222"
    networks:
      - honeypot_net
  
# Windows Server Honeypot

  honeypot-windows:
    image: your-honeypot-image
    environment:
      - HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=windows_server
      - HONEYPOT_SSH_PORT=3390
      - HONEYPOT_SSH_SERVER_NAME=WIN-SRV-2022-PROD
      - HONEYPOT_SSH_BANNER=SSH-2.0-OpenSSH_for_Windows_8.1
    ports:
      - "3390:3390"
    networks:
      - honeypot_net
  
# CentOS Honeypot

  honeypot-centos:
    image: your-honeypot-image
    environment:
      - HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=linux_centos
      - HONEYPOT_SSH_PORT=2223
      - HONEYPOT_SSH_SERVER_NAME=centos-stream-9
    ports:
      - "2223:2223"
    networks:
      - honeypot_net

networks:
  honeypot_net:
    external: true
"""

# Quick test script

TEST_WINDOWS_HONEYPOT = """

# !/usr/bin/env python3

# Test Windows Server honeypot emulation

import asyncio
from plugins.honeypot.config import HoneypotConfig
from plugins.honeypot.engine.ssh_handler import SSHHandler

async def test_windows_emulation():
    # Configure for Windows Server
    config = HoneypotConfig()
    config.emulation.enabled = True
    config.emulation.default_os_profile = "windows_server"

    handler = SSHHandler(config)
    
    print(f"Windows Server Honeypot Configuration:")
    print(f"  OS Profile: {handler._fingerprint_profile.profile_id}")
    print(f"  OS Version: {handler._fingerprint_profile.os_version}")
    print(f"  Hostname: {handler._fingerprint_profile.hostname}")
    print(f"  SSH Banner: {handler._fingerprint_profile.ssh_banner}")
    
    # Test commands
    session_id = "windows-test-session"
    
    print("\\nTesting Windows commands:")
    
    # PowerShell-style commands
    output = await handler._generate_command_response(session_id, "dir", "Administrator")
    print(f"  dir → {output[:60]}...")
    
    output = await handler._generate_command_response(session_id, "whoami", "Administrator")
    print(f"  whoami → {output}")
    
    output = await handler._generate_command_response(session_id, "systeminfo", "Administrator")
    print(f"  systeminfo → {output[:80]}...")

if __name__ == "__main__":
    asyncio.run(test_windows_emulation())
"""

print("✅ Windows Server Honeypot Configuration Created")
print("\nOptions for deployment:")
print("1. Single Windows instance: Set HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=windows_server")
print("2. Multi-OS deployment: Use Docker Compose with different profiles per container")
print("3. Port forwarding: Linux on 2222, Windows on 3390, CentOS on 2223")
