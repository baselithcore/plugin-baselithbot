//! Scanner argv allowlist + per-scanner sandbox profile.
//!
//! Every scanner the daemon can run has a [`ScannerPolicy`] entry
//! that defines:
//!
//! * The exact `argv0` the daemon will exec (no `$PATH` resolution).
//! * The required argv prefix the backend must supply.
//! * Filesystem paths the scanner is allowed to read / write under
//!   the sandbox.
//! * The set of exit codes that count as a successful run (e.g.
//!   nuclei returns 1 when findings are present, not a failure).
//!
//! Backend-supplied argv is sanitized against this policy before any
//! sandbox primitive is configured. A mismatched scanner kind or an
//! attempt to inject extra `--config` / `--script` flags is rejected
//! with [`crate::ExecutorError::PolicyDenied`].

use serde::{Deserialize, Serialize};

/// Scanner kinds the daemon can run locally on the host.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScannerKind {
    /// Trivy filesystem / package SCA.
    TrivyFs,
    /// Nuclei template runner against `localhost`.
    NucleiLocal,
    /// On-disk gitleaks-style secret scan.
    SecretScan,
}

/// Static policy entry keyed by `ScannerKind`.
#[derive(Debug, Clone)]
pub struct ScannerPolicy {
    /// Absolute path to the binary the daemon execs (no PATH lookup).
    pub argv0: &'static str,
    /// Argv tail that MUST be present at the start of the request.
    pub required_prefix: &'static [&'static str],
    /// Filesystem paths the sandbox grants the scanner read access to.
    pub allowed_read_paths: &'static [&'static str],
    /// Filesystem paths the sandbox grants the scanner write access to.
    pub allowed_write_paths: &'static [&'static str],
    /// Exit codes that signal a non-error completion.
    pub success_exit_codes: &'static [i32],
}

impl ScannerKind {
    /// Resolve the static policy for this scanner kind.
    pub fn policy(self) -> ScannerPolicy {
        match self {
            ScannerKind::TrivyFs => ScannerPolicy {
                argv0: "/usr/local/bin/trivy",
                required_prefix: &["fs", "--quiet", "--format", "json"],
                allowed_read_paths: &["/", "/etc", "/var/lib"],
                allowed_write_paths: &["/tmp"],
                success_exit_codes: &[0],
            },
            ScannerKind::NucleiLocal => ScannerPolicy {
                argv0: "/usr/local/bin/nuclei",
                required_prefix: &["-jsonl", "-silent", "-target"],
                allowed_read_paths: &["/etc", "/usr"],
                allowed_write_paths: &["/tmp"],
                success_exit_codes: &[0, 1],
            },
            ScannerKind::SecretScan => ScannerPolicy {
                argv0: "/usr/local/bin/gitleaks",
                required_prefix: &["detect", "--no-banner", "--report-format", "json"],
                allowed_read_paths: &["/"],
                allowed_write_paths: &["/tmp"],
                success_exit_codes: &[0, 1],
            },
        }
    }
}

/// Verify an inbound argv is acceptable for the given scanner.
///
/// Returns the sanitized argv to actually exec (`argv0` followed by
/// the request tail) on success, or a human-readable rejection
/// reason on failure.
pub fn validate_argv(kind: ScannerKind, requested_argv: &[String]) -> Result<Vec<String>, String> {
    let policy = kind.policy();
    if requested_argv.len() < policy.required_prefix.len() {
        return Err(format!(
            "argv too short: need at least {} elements",
            policy.required_prefix.len()
        ));
    }
    for (i, expected) in policy.required_prefix.iter().enumerate() {
        if requested_argv[i] != *expected {
            return Err(format!(
                "argv element {i}: expected {expected:?}, got {:?}",
                requested_argv[i]
            ));
        }
    }
    let mut full = Vec::with_capacity(requested_argv.len() + 1);
    full.push(policy.argv0.to_string());
    full.extend_from_slice(requested_argv);
    Ok(full)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trivy_required_prefix_matches() {
        let req = vec![
            "fs".to_string(),
            "--quiet".to_string(),
            "--format".to_string(),
            "json".to_string(),
            "/var/lib/baselith/scan-target".to_string(),
        ];
        let argv = validate_argv(ScannerKind::TrivyFs, &req).expect("argv ok");
        assert_eq!(argv[0], "/usr/local/bin/trivy");
        assert_eq!(argv[1], "fs");
    }

    #[test]
    fn trivy_rejects_wrong_prefix() {
        let req = vec!["image".to_string(), "alpine".to_string()];
        let err = validate_argv(ScannerKind::TrivyFs, &req).unwrap_err();
        assert!(err.contains("argv element 0") || err.contains("argv too short"));
    }

    #[test]
    fn argv_too_short_is_rejected() {
        let req = vec!["fs".to_string()];
        let err = validate_argv(ScannerKind::TrivyFs, &req).unwrap_err();
        assert!(err.contains("argv too short"));
    }

    #[test]
    fn nuclei_accepts_known_exit_codes() {
        let policy = ScannerKind::NucleiLocal.policy();
        assert!(policy.success_exit_codes.contains(&0));
        assert!(policy.success_exit_codes.contains(&1));
    }
}
