//! Local scanner executor.
//!
//! Runs scanner binaries on the host inside a per-platform sandbox:
//!
//! * **linux** — `landlock` filesystem isolation + `seccompiler` syscall
//!   filter + cgroup v2 resource caps + `setns` UID/GID drop.
//! * **macOS** — `sandbox-exec` profile (deprecated but still
//!   supported) + `posix_spawn` resource caps.
//!
//! Phase 1 ships the [`run_sandboxed`] entrypoint: argv allowlist
//! check, wall-clock timeout, output capping, and per-platform
//! sandbox wrapping. The eBPF / ESF integrations for run-time
//! observation land in Phase 2 alongside the collector.

#![deny(unsafe_code)]
#![warn(missing_docs)]

pub mod policy;
pub mod runner;

use thiserror::Error;

pub use policy::{ScannerKind, ScannerPolicy};
pub use runner::{run_sandboxed, ExecOutcome, ExecRequest, ResourceLimits};

/// Failures the executor can surface back to the backend as
/// `CommandResult.error_code`.
#[derive(Debug, Error)]
pub enum ExecutorError {
    /// Argv passed by the backend was rejected by the local policy.
    #[error("argv rejected by policy: {0}")]
    PolicyDenied(String),

    /// Launching the scanner failed.
    #[error("spawn failed: {0}")]
    Spawn(String),

    /// The scanner exceeded its wall-clock budget.
    #[error("wall timeout exceeded")]
    Timeout,

    /// The scanner exited with a non-zero code outside the
    /// allowed-exit-code set documented per scanner.
    #[error("scanner exited {code}")]
    ExitCode {
        /// Numeric exit status returned by the scanner.
        code: i32,
    },

    /// Output exceeded the per-invocation cap.
    #[error("output truncated: {limit_bytes} bytes")]
    OutputTooLarge {
        /// Cap that was hit.
        limit_bytes: usize,
    },
}

/// Default wall-clock cap if the request leaves it unset.
pub const DEFAULT_WALL_TIMEOUT_SECS: u64 = 300;

/// Default per-invocation stdout/stderr cap.
pub const DEFAULT_OUTPUT_CAP_BYTES: usize = 4 * 1024 * 1024;
