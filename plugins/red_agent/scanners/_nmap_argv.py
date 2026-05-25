"""Argv construction for the nmap scanner.

Extracted from :mod:`plugins.red_agent.scanners.nmap` so that the main
adapter stays under the project's 500-line file cap. The module is
intentionally pure: every helper is a function over plain values and
never invokes a shell — every argv element is appended explicitly.

The :func:`build_argv` entry point starts from an immutable per-intensity
profile and layers any overrides found in ``target.metadata["nmap"]``
under strict validation. Categories that mutate state on the target
(``exploit``/``dos``/``brute``/``intrusive``/``malware``) are gated
behind both INTRUSIVE intensity and an explicit
``allow_dangerous_categories=True`` consent flag.
"""

from __future__ import annotations

import re
import shlex
from typing import Final
from urllib.parse import urlparse

from plugins.red_agent.models import ScanIntensity, Target, TargetType

# Nmap flag profiles. ``-sT`` (TCP connect) avoids raw-socket privileges
# so scans run under the sandbox's --cap-drop=ALL. ``-Pn`` skips host
# discovery (target list is operator-supplied, not arbitrary). ``-n``
# disables reverse-DNS to avoid leaking target hostnames via the
# resolver. ``--open`` filters closed/filtered ports so findings are
# actionable. ``-oX -`` streams XML to stdout for the parser.
_PROFILE_PASSIVE: Final = (
    "-sT -Pn -n --top-ports 100 -T3 --max-retries 1 --host-timeout 3m --open -oX -"
)
_PROFILE_ACTIVE: Final = (
    "-sT -sV -Pn -n --top-ports 1000 --version-intensity 7 "
    "-T4 --max-retries 2 --host-timeout 8m --open "
    '--script "default,discovery,version,safe" -oX -'
)
# INTRUSIVE adds the ``vuln`` and ``auth`` categories — both are
# documented as non-exploitative in the Nmap NSE category guide. Full
# TCP range (``-p-``) is intentional: at INTRUSIVE we trade duration
# for completeness (e.g. services bound to 8443/9200/27017/etc.).
_PROFILE_INTRUSIVE: Final = (
    "-sT -sV -Pn -n -p- --version-all "
    "-T4 --max-retries 2 --host-timeout 20m --open "
    '--script "default,discovery,version,safe,vuln,auth" '
    "--script-timeout 2m -oX -"
)

PROFILES: Final[dict[ScanIntensity, str]] = {
    ScanIntensity.PASSIVE: _PROFILE_PASSIVE,
    ScanIntensity.ACTIVE: _PROFILE_ACTIVE,
    ScanIntensity.INTRUSIVE: _PROFILE_INTRUSIVE,
}

SAFE_NSE_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"default", "discovery", "version", "safe", "vuln", "auth"}
)
DANGEROUS_NSE_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"exploit", "dos", "brute", "intrusive", "malware"}
)
# Allowlist for individual NSE script ids accepted via ``extra_scripts``.
# Conservative pattern: alnum + dash + dot, ≤64 chars. Refuses anything
# else to keep argv flat and predictable.
_NSE_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9.\-]{0,63}$")
# Restrictive port-spec validator. Accepts numeric tokens, ranges, and
# ``T:``/``U:`` prefixes. Rejects shell metacharacters.
_PORT_SPEC_RE: Final[re.Pattern[str]] = re.compile(
    r"^[TU]?:?[\d,\-]+(?:,[TU]?:?[\d,\-]+)*$"
)


def nmap_target(target: Target) -> str:
    """Map a :class:`Target` to a host/IP/CIDR nmap accepts.

    Nmap rejects URL forms ("Unable to split netmask from target
    expression"), so URL targets are reduced to their hostname.
    """
    if target.type == TargetType.URL:
        host = urlparse(target.value).hostname
        if host:
            return host
    return target.value


def build_argv(target: Target, intensity: ScanIntensity) -> list[str]:
    """Build the nmap argv for ``target`` at ``intensity``.

    Override surface (``target.metadata["nmap"]``):

    * ``extra_scripts``: ``list[str]`` — categories or specific NSE ids
      added to ``--script``. Categories in
      :data:`DANGEROUS_NSE_CATEGORIES` require both INTRUSIVE intensity
      and ``allow_dangerous_categories=True``; otherwise dropped.
      Specific script ids must match :data:`_NSE_ID_RE`.
    * ``port_spec``: ``str`` — replaces the default port selector
      (``--top-ports``/``-F``/``-p-``). Validated against
      :data:`_PORT_SPEC_RE`.
    * ``version_intensity``: ``int`` in [0, 9] — overrides ``-sV`` probe
      intensity. Ignored at PASSIVE (no ``-sV``).
    * ``allow_dangerous_categories``: ``bool`` — explicit consent for
      ``exploit``/``dos``/``brute``/etc. Honored only at INTRUSIVE.

    The function never invokes a shell — every value lands as its own
    argv element. Invalid overrides are silently dropped; logging is
    left to the caller to keep this helper pure and unit-testable.
    """
    profile = PROFILES.get(intensity, _PROFILE_PASSIVE)
    argv = shlex.split(profile)
    overrides_raw = (target.metadata or {}).get("nmap")
    overrides: dict[str, object] = (
        overrides_raw if isinstance(overrides_raw, dict) else {}
    )
    allow_dangerous = bool(overrides.get("allow_dangerous_categories"))

    extras = _validated_extra_scripts(
        overrides.get("extra_scripts"), intensity, allow_dangerous
    )
    if extras:
        argv = _augment_script_list(argv, extras)

    port_spec = overrides.get("port_spec")
    if isinstance(port_spec, str) and _PORT_SPEC_RE.match(port_spec):
        argv = _replace_port_selector(argv, port_spec)

    if intensity is not ScanIntensity.PASSIVE:
        vi = overrides.get("version_intensity")
        if isinstance(vi, int) and 0 <= vi <= 9:
            argv = _replace_version_intensity(argv, vi)

    argv.append(nmap_target(target))
    return argv


def _validated_extra_scripts(
    raw: object, intensity: ScanIntensity, allow_dangerous: bool
) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        token = item.strip().lower()
        if not token:
            continue
        if token in SAFE_NSE_CATEGORIES:
            out.append(token)
            continue
        if token in DANGEROUS_NSE_CATEGORIES:
            if allow_dangerous and intensity is ScanIntensity.INTRUSIVE:
                out.append(token)
            continue
        if _NSE_ID_RE.match(token):
            out.append(token)
    return out


def _augment_script_list(argv: list[str], extras: list[str]) -> list[str]:
    """Merge ``extras`` into the existing ``--script`` argument (or
    append a new ``--script`` pair when none exists).
    """
    new_argv = list(argv)
    for i, tok in enumerate(new_argv):
        if tok == "--script" and i + 1 < len(new_argv):
            existing = [p.strip() for p in new_argv[i + 1].split(",") if p.strip()]
            merged = list(dict.fromkeys([*existing, *extras]))
            new_argv[i + 1] = ",".join(merged)
            return new_argv
    new_argv.extend(["--script", ",".join(extras)])
    return new_argv


def _replace_port_selector(argv: list[str], port_spec: str) -> list[str]:
    """Replace ``--top-ports``/``-F``/``-p-`` selectors with
    ``-p <spec>``.
    """
    skip_next = False
    out: list[str] = []
    for tok in argv:
        if skip_next:
            skip_next = False
            continue
        if tok == "--top-ports":
            skip_next = True
            continue
        if tok in {"-F", "-p-"}:
            continue
        out.append(tok)
    out.extend(["-p", port_spec])
    return out


def _replace_version_intensity(argv: list[str], value: int) -> list[str]:
    out: list[str] = []
    skip_next = False
    seen = False
    for tok in argv:
        if skip_next:
            skip_next = False
            seen = True
            out.append(str(value))
            continue
        if tok == "--version-intensity":
            skip_next = True
            out.append(tok)
            continue
        out.append(tok)
    if not seen:
        out.extend(["--version-intensity", str(value)])
    return out
