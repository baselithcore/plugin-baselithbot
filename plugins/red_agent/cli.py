"""Red Agent CLI integration.

Registers a `red-agent` subcommand under the `baselith` CLI:

    baselith red-agent scan <url> [--intensity passive|active|intrusive]
    baselith red-agent preflight <url>

The CLI talks to a running Red Agent backend over HTTP — it does not
construct an in-process agent. This keeps the CLI thin and avoids
booting Postgres/FalkorDB just to fire a scan.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def register_parser(subparsers: Any, formatter_class: Any) -> None:
    parser = subparsers.add_parser(
        "red-agent",
        help="Operate the Red Agent (scan / preflight / status)",
        formatter_class=formatter_class,
    )
    sub = parser.add_subparsers(dest="ra_command", required=True)

    scan = sub.add_parser(
        "scan", help="Submit a new scan", formatter_class=formatter_class
    )
    scan.add_argument("target", help="URL or hostname to scan")
    scan.add_argument(
        "--intensity",
        choices=["passive", "active", "intrusive"],
        default="passive",
    )
    scan.add_argument(
        "--scanners",
        default="nmap,nuclei",
        help="Comma-separated scanner list",
    )
    scan.set_defaults(handler=_cmd_scan)

    pre = sub.add_parser(
        "preflight",
        help="Run guardrail pre-flight without submitting",
        formatter_class=formatter_class,
    )
    pre.add_argument("target", help="URL or hostname to validate")
    pre.add_argument(
        "--intensity",
        choices=["passive", "active", "intrusive"],
        default="passive",
    )
    pre.add_argument("--scanners", default="nmap,nuclei")
    pre.set_defaults(handler=_cmd_preflight)

    status = sub.add_parser(
        "status",
        help="Fetch a scan's status + findings",
        formatter_class=formatter_class,
    )
    status.add_argument("scan_id")
    status.set_defaults(handler=_cmd_status)

    doctor = sub.add_parser(
        "doctor",
        help="Validate Red Agent environment + reachability",
        formatter_class=formatter_class,
    )
    doctor.set_defaults(handler=_cmd_doctor)


def _api_base() -> str:
    return os.environ.get("BASELITH_API_BASE", "http://localhost:8000").rstrip("/")


def _token() -> str:
    return os.environ.get("BASELITH_API_TOKEN", "")


def _request(method: str, path: str, payload: Any = None) -> Any:
    req = urllib.request.Request(
        url=f"{_api_base()}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            return json.loads(resp.read() or "null")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.stderr.write(f"HTTP {e.code}: {body}\n")
        sys.exit(2)


def _target_type(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return "url"
    if "/" in value and value.split("/")[-1].isdigit():
        return "cidr"
    return "hostname"


def _cmd_scan(args: argparse.Namespace) -> int:
    body = {
        "target": {"type": _target_type(args.target), "value": args.target},
        "scanners": [s.strip() for s in args.scanners.split(",") if s.strip()],
        "intensity": args.intensity,
    }
    res = _request("POST", "/red-agent/scans", body)
    print(json.dumps(res, indent=2))
    return 0


def _cmd_preflight(args: argparse.Namespace) -> int:
    body = {
        "target": {"type": _target_type(args.target), "value": args.target},
        "scanners": [s.strip() for s in args.scanners.split(",") if s.strip()],
        "intensity": args.intensity,
    }
    res = _request("POST", "/red-agent/guardrails/preflight", body)
    print(json.dumps(res, indent=2))
    return 0 if res.get("allowed") else 1


def _cmd_status(args: argparse.Namespace) -> int:
    res = _request("GET", f"/red-agent/scans/{args.scan_id}")
    print(json.dumps(res, indent=2))
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    del args
    findings: list[tuple[str, bool, str]] = []

    # 1. Local config sanity
    try:
        from plugins.red_agent.config import RedAgentConfig

        cfg = RedAgentConfig()
        findings.append(("config.load", True, f"sandbox={cfg.sandbox_provider}"))
        if not cfg.scope_allowlist and not cfg.bug_bounty_mode:
            findings.append(
                (
                    "scope.policy",
                    False,
                    "scope_allowlist empty and bug_bounty_mode disabled — "
                    "every scan will be blocked by guardrails",
                )
            )
        else:
            findings.append(
                (
                    "scope.policy",
                    True,
                    f"allowlist entries={len(cfg.scope_allowlist)}, "
                    f"bug_bounty={cfg.bug_bounty_mode}",
                )
            )
        if cfg.allow_internal_targets:
            findings.append(
                (
                    "ssrf.policy",
                    False,
                    "RED_AGENT_ALLOW_INTERNAL_TARGETS=true — "
                    "private/loopback targets allowed (lab only).",
                )
            )
        else:
            findings.append(("ssrf.policy", True, "private targets blocked"))
    except Exception as e:  # noqa: BLE001
        findings.append(("config.load", False, str(e)))

    # 2. Backend reachability
    try:
        res = _request("GET", "/red-agent/health")
        ok = isinstance(res, dict) and res.get("status") == "ok"
        findings.append(
            (
                "backend.health",
                ok,
                f"{_api_base()} → {res.get('status') if isinstance(res, dict) else 'unknown'}",
            )
        )
    except SystemExit:
        findings.append(("backend.health", False, f"{_api_base()} unreachable"))

    # 3. Auth token presence
    findings.append(
        (
            "auth.token",
            bool(_token()),
            "BASELITH_API_TOKEN " + ("set" if _token() else "MISSING"),
        )
    )

    pad = max(len(name) for name, _, _ in findings)
    code = 0
    for name, ok, detail in findings:
        marker = "✓" if ok else "✗"
        line = f"  {marker} {name.ljust(pad)}  {detail}"
        sys.stdout.write(line + "\n")
        if not ok:
            code = 1
    return code
