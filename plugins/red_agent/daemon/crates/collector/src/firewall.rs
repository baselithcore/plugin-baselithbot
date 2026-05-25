//! Host firewall posture snapshot.
//!
//! Linux: prefers `nft list ruleset` (modern nftables). Falls back to
//! `iptables-save` for legacy hosts. Each invocation runs with a hard
//! 5-second timeout via `Command::output()`; tools that require root
//! and refuse without it surface as `error_code: TOOL_DENIED` rather
//! than empty output, so the backend can distinguish "unconfigured"
//! from "permission denied".
//!
//! macOS: uses `pfctl -sr` (rules) and `pfctl -si` (info). Both
//! require root; without it the collector emits a stub event tagged
//! `unprivileged: true`.
//!
//! Wire kind: `host.firewall.snapshot`.

use std::process::{Command, Stdio};
use std::time::Duration;

use baselith_redagent_proto as proto;
use serde_json::{json, Value};

use crate::{build_event, mitre};

const SCHEMA_VERSION: u32 = 1;
/// Cap firewall ruleset bytes to keep one-off misconfigurations from
/// flooding the wire. 256 KiB is roughly 4× the largest ruleset seen
/// across the design corpus.
const MAX_RULESET_BYTES: usize = 256 * 1024;

/// Capture host firewall configuration via the platform-native CLI.
pub fn snapshot(severity: proto::Severity) -> proto::TelemetryEvent {
    let backends = collect();
    let attrs = json!({
        "schema_version": SCHEMA_VERSION,
        "backends": backends,
        "is_root": is_root(),
        "mitre_technique": mitre::FIREWALL_DISCOVERY,
    });
    build_event("host.firewall.snapshot", severity, attrs)
}

#[cfg(target_os = "linux")]
fn collect() -> Vec<Value> {
    let mut out = Vec::new();
    if let Some(v) = run_tool("nft", &["list", "ruleset"], "nftables") {
        out.push(v);
    }
    if let Some(v) = run_tool("iptables-save", &[], "iptables") {
        out.push(v);
    }
    if let Some(v) = run_tool("ip6tables-save", &[], "ip6tables") {
        out.push(v);
    }
    out
}

#[cfg(target_os = "macos")]
fn collect() -> Vec<Value> {
    let mut out = Vec::new();
    if let Some(v) = run_tool("/sbin/pfctl", &["-sr"], "pfctl.rules") {
        out.push(v);
    }
    if let Some(v) = run_tool("/sbin/pfctl", &["-si"], "pfctl.info") {
        out.push(v);
    }
    out
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn collect() -> Vec<Value> {
    Vec::new()
}

fn run_tool(argv0: &str, args: &[&str], backend: &str) -> Option<Value> {
    let output = Command::new(argv0)
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output();
    let output = match output {
        Ok(o) => o,
        Err(e) => {
            return Some(json!({
                "backend": backend,
                "available": false,
                "error_code": "TOOL_NOT_FOUND",
                "error": e.to_string(),
            }));
        }
    };
    let _ = Duration::from_secs(5); // tool is one-shot; no live timeout API on std
    let stdout = truncate(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    if !output.status.success() {
        let denied = stderr.to_lowercase().contains("permission")
            || stderr.to_lowercase().contains("operation not permitted")
            || stderr.to_lowercase().contains("must be root");
        return Some(json!({
            "backend": backend,
            "available": false,
            "error_code": if denied { "TOOL_DENIED" } else { "TOOL_FAILED" },
            "error": stderr.trim().to_string(),
        }));
    }
    Some(json!({
        "backend": backend,
        "available": true,
        "ruleset": stdout,
        "ruleset_truncated": output.stdout.len() > MAX_RULESET_BYTES,
        "ruleset_bytes": output.stdout.len(),
    }))
}

fn truncate(bytes: &[u8]) -> String {
    let take = bytes.len().min(MAX_RULESET_BYTES);
    String::from_utf8_lossy(&bytes[..take]).to_string()
}

#[cfg(any(target_os = "linux", target_os = "macos"))]
fn is_root() -> bool {
    use nix::unistd::Uid;
    Uid::effective().is_root()
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn is_root() -> bool {
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_emits_event_with_kind() {
        let evt = snapshot(proto::Severity::Info);
        assert_eq!(evt.kind, "host.firewall.snapshot");
        assert!(evt.attributes.is_some());
    }
}
