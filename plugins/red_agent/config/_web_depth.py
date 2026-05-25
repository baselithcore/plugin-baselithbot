"""Deep web-app scanner configuration mixin.

Schemathesis already covers REST OpenAPI fuzzing. The three scanners
behind this mixin extend the coverage to areas the OpenAPI fuzzer
cannot reach:

- ``graphql_audit`` — introspection-on detection, alias-overload,
  field-suggestion leakage, batch-attack vector check.
- ``jwt_audit`` — token-attack heuristics for sample JWTs supplied
  via ``Target.metadata['jwt_samples']``: ``alg=none`` acceptance,
  weak HS256 secret (small built-in wordlist), ``kid`` path
  traversal, ``jku`` / ``x5u`` redirection.
- ``waf_evasion`` — wafw00f-style WAF fingerprint plus three
  payload-encoding evasion checks. INTRUSIVE intensity only — every
  request is intentionally suspicious.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class _WebDepthConfig(BaseModel):
    graphql_audit_enabled: bool = Field(
        default=True,
        description=(
            "Enable the GraphQL auditor. Read-only (introspection + "
            "shape probes); safe to leave on."
        ),
    )
    graphql_audit_request_timeout_seconds: float = Field(
        default=15.0,
        description="HTTP timeout per GraphQL probe.",
    )

    jwt_audit_enabled: bool = Field(
        default=True,
        description=(
            "Enable the JWT auditor. Operates on sample tokens "
            "supplied via target metadata; never crafts requests."
        ),
    )
    jwt_audit_hs256_wordlist_path: str | None = Field(
        default=None,
        description=(
            "Path to a newline-delimited list of candidate HS256 "
            "secrets. When unset the auditor uses a built-in 32-entry "
            "list of the most common weak secrets seen in CTFs and "
            "leaked dumps."
        ),
    )

    waf_evasion_enabled: bool = Field(
        default=False,
        description=(
            "Enable the WAF-evasion check. INTRUSIVE only — every "
            "probe is intentionally suspicious traffic."
        ),
    )
    waf_evasion_request_timeout_seconds: float = Field(
        default=10.0,
        description="HTTP timeout per WAF-evasion probe.",
    )
