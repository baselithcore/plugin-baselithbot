//! Persistence / autostart enumeration.
//!
//! Surfaces the canonical OS-level locations attackers abuse to keep
//! code running across reboots. Each finding carries the file path, a
//! sha256 (hashed at observation time), and the modification time so
//! the backend can correlate against deployment baselines.
//!
//! Locations covered (Phase 1):
//!
//! Linux:
//!   * `/etc/cron.{hourly,daily,weekly,monthly,d}/`
//!   * `/var/spool/cron/`, `/var/spool/cron/crontabs/`
//!   * `/etc/systemd/system/`, `/usr/lib/systemd/system/`
//!   * `/etc/init.d/`
//!   * `/etc/rc.local`
//!   * `/etc/xdg/autostart/`, `/home/*/.config/autostart/`
//!
//! macOS:
//!   * `/Library/LaunchDaemons/`, `/Library/LaunchAgents/`
//!   * `/System/Library/LaunchDaemons/`, `/System/Library/LaunchAgents/`
//!   * `/Users/*/Library/LaunchAgents/`
//!
//! Wire kind: `host.persistence.snapshot`.

use std::path::{Path, PathBuf};

use baselith_redagent_proto as proto;
use serde_json::{json, Value};

use crate::{build_event, hash::hash_file, mitre};

const SCHEMA_VERSION: u32 = 1;
/// Hard cap on total entries to keep batch size bounded on noisy hosts.
const MAX_ENTRIES: usize = 512;

/// Capture persistence / autostart entries across the canonical
/// OS-level locations.
pub fn snapshot(severity: proto::Severity) -> proto::TelemetryEvent {
    let entries = collect();
    let count = entries.len();
    let truncated = count >= MAX_ENTRIES;
    let attrs = json!({
        "schema_version": SCHEMA_VERSION,
        "entries": entries,
        "count": count,
        "truncated": truncated,
    });
    build_event("host.persistence.snapshot", severity, attrs)
}

fn collect() -> Vec<Value> {
    let mut out: Vec<Value> = Vec::new();
    for (kind, dir) in autostart_dirs() {
        scan_dir(Path::new(dir), kind, &mut out);
        if out.len() >= MAX_ENTRIES {
            break;
        }
    }
    for (kind, path) in autostart_files() {
        if Path::new(path).is_file() {
            out.push(describe(Path::new(path), kind));
            if out.len() >= MAX_ENTRIES {
                break;
            }
        }
    }
    if out.len() < MAX_ENTRIES {
        for (kind, glob_root) in user_autostart_roots() {
            scan_user_glob(Path::new(glob_root), kind, &mut out);
            if out.len() >= MAX_ENTRIES {
                break;
            }
        }
    }
    out.truncate(MAX_ENTRIES);
    out
}

#[cfg(target_os = "linux")]
fn autostart_dirs() -> Vec<(&'static str, &'static str)> {
    vec![
        ("cron.hourly", "/etc/cron.hourly"),
        ("cron.daily", "/etc/cron.daily"),
        ("cron.weekly", "/etc/cron.weekly"),
        ("cron.monthly", "/etc/cron.monthly"),
        ("cron.d", "/etc/cron.d"),
        ("crontabs", "/var/spool/cron/crontabs"),
        ("crontabs", "/var/spool/cron"),
        ("systemd.etc", "/etc/systemd/system"),
        ("systemd.usrlib", "/usr/lib/systemd/system"),
        ("systemd.lib", "/lib/systemd/system"),
        ("init.d", "/etc/init.d"),
        ("xdg.autostart", "/etc/xdg/autostart"),
    ]
}

#[cfg(target_os = "linux")]
fn autostart_files() -> Vec<(&'static str, &'static str)> {
    vec![("rc.local", "/etc/rc.local"), ("crontab", "/etc/crontab")]
}

#[cfg(target_os = "linux")]
fn user_autostart_roots() -> Vec<(&'static str, &'static str)> {
    vec![("xdg.autostart.user", "/home")]
}

#[cfg(target_os = "macos")]
fn autostart_dirs() -> Vec<(&'static str, &'static str)> {
    vec![
        ("LaunchDaemon", "/Library/LaunchDaemons"),
        ("LaunchAgent", "/Library/LaunchAgents"),
        ("LaunchDaemon.system", "/System/Library/LaunchDaemons"),
        ("LaunchAgent.system", "/System/Library/LaunchAgents"),
    ]
}

#[cfg(target_os = "macos")]
fn autostart_files() -> Vec<(&'static str, &'static str)> {
    vec![]
}

#[cfg(target_os = "macos")]
fn user_autostart_roots() -> Vec<(&'static str, &'static str)> {
    vec![("LaunchAgent.user", "/Users")]
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn autostart_dirs() -> Vec<(&'static str, &'static str)> {
    Vec::new()
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn autostart_files() -> Vec<(&'static str, &'static str)> {
    Vec::new()
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn user_autostart_roots() -> Vec<(&'static str, &'static str)> {
    Vec::new()
}

fn scan_dir(dir: &Path, kind: &str, out: &mut Vec<Value>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        if out.len() >= MAX_ENTRIES {
            return;
        }
        let path = entry.path();
        if path.is_file() {
            out.push(describe(&path, kind));
        }
    }
}

#[cfg(any(target_os = "linux", target_os = "macos"))]
fn scan_user_glob(root: &Path, kind: &str, out: &mut Vec<Value>) {
    // /home/<user>/.config/autostart  (linux)
    // /Users/<user>/Library/LaunchAgents  (macOS)
    let suffix: &Path = if cfg!(target_os = "linux") {
        Path::new(".config/autostart")
    } else {
        Path::new("Library/LaunchAgents")
    };
    let Ok(home_entries) = std::fs::read_dir(root) else {
        return;
    };
    for home in home_entries.flatten() {
        if out.len() >= MAX_ENTRIES {
            return;
        }
        let user_dir: PathBuf = home.path().join(suffix);
        if user_dir.is_dir() {
            scan_dir(&user_dir, kind, out);
        }
    }
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn scan_user_glob(_root: &Path, _kind: &str, _out: &mut Vec<Value>) {}

fn describe(path: &Path, kind: &str) -> Value {
    let metadata = std::fs::metadata(path).ok();
    let size = metadata.as_ref().map(|m| m.len());
    let mtime = metadata.as_ref().and_then(|m| {
        m.modified()
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_secs())
    });
    let digest = hash_file(path);
    json!({
        "kind": kind,
        "path": digest.path,
        "sha256": digest.sha256,
        "size_bytes": size,
        "mtime_unix": mtime,
        "error_code": digest.error_code,
        "mitre_technique": mitre::persistence_technique(kind),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_emits_event_with_kind() {
        let evt = snapshot(proto::Severity::Info);
        assert_eq!(evt.kind, "host.persistence.snapshot");
        assert!(evt.attributes.is_some());
    }

    #[test]
    fn collect_does_not_panic_on_missing_dirs() {
        // Even on a host with no privileged paths the collector must
        // return cleanly.
        let v = collect();
        assert!(v.len() <= MAX_ENTRIES);
    }
}
