//! Kernel-module / kext inventory.
//!
//! Linux: parses `/proc/modules`. Each line is
//! `<name> <size> <use_count> <dependents> <state> <load_address>`.
//! Out-of-tree modules are inferred from the `taint` field of
//! `/proc/sys/kernel/tainted` exposed alongside the list.
//!
//! macOS: shells out to `/usr/sbin/kextstat -l`. Output columns:
//! `Index Refs Address Size Wired Name (Version) UUID <Linked Against>`.
//! The collector keeps only the parsed name + version + signing status
//! (System Integrity Protection refuses unsigned kexts since macOS 10.13).
//!
//! Wire kind: `host.kernel.modules`.

use baselith_redagent_proto as proto;
use serde_json::{json, Value};

use crate::{build_event, mitre};

const SCHEMA_VERSION: u32 = 1;

/// Capture loaded kernel modules / kexts.
pub fn snapshot(severity: proto::Severity) -> proto::TelemetryEvent {
    let modules = collect_modules();
    let tainted = read_tainted();
    let attrs = json!({
        "schema_version": SCHEMA_VERSION,
        "modules": modules,
        "count": modules.len(),
        "tainted": tainted,
        "mitre_technique": mitre::KERNEL_MODULES,
    });
    build_event("host.kernel.modules", severity, attrs)
}

#[cfg(target_os = "linux")]
fn collect_modules() -> Vec<Value> {
    let Ok(text) = std::fs::read_to_string("/proc/modules") else {
        return Vec::new();
    };
    text.lines()
        .filter_map(|line| {
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() < 4 {
                return None;
            }
            Some(json!({
                "name": parts[0],
                "size_bytes": parts[1].parse::<u64>().unwrap_or(0),
                "use_count": parts[2].parse::<u32>().unwrap_or(0),
                "dependents": parts[3],
                "state": parts.get(4).copied().unwrap_or("unknown"),
            }))
        })
        .collect()
}

#[cfg(target_os = "linux")]
fn read_tainted() -> Option<u64> {
    std::fs::read_to_string("/proc/sys/kernel/tainted")
        .ok()
        .and_then(|s| s.trim().parse::<u64>().ok())
}

#[cfg(target_os = "macos")]
fn collect_modules() -> Vec<Value> {
    use std::process::Command;
    let Ok(output) = Command::new("/usr/sbin/kextstat").arg("-l").output() else {
        return Vec::new();
    };
    if !output.status.success() {
        return Vec::new();
    }
    let text = String::from_utf8_lossy(&output.stdout);
    text.lines().filter_map(parse_kextstat_line).collect()
}

#[cfg(target_os = "macos")]
fn parse_kextstat_line(line: &str) -> Option<Value> {
    let parts: Vec<&str> = line.split_whitespace().collect();
    if parts.len() < 6 {
        return None;
    }
    // Index Refs Address Size Wired Name (Version) UUID
    let name = parts[5];
    let version = parts
        .get(6)
        .map(|s| s.trim_matches(|c| c == '(' || c == ')'));
    Some(json!({
        "name": name,
        "version": version,
        "size_bytes": u64::from_str_radix(parts[3].trim_start_matches("0x"), 16).unwrap_or(0),
        "refs": parts[1].parse::<u32>().unwrap_or(0),
    }))
}

#[cfg(target_os = "macos")]
fn read_tainted() -> Option<u64> {
    None
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn collect_modules() -> Vec<Value> {
    Vec::new()
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn read_tainted() -> Option<u64> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_emits_event_with_kind() {
        let evt = snapshot(proto::Severity::Info);
        assert_eq!(evt.kind, "host.kernel.modules");
        assert!(evt.attributes.is_some());
    }
}
