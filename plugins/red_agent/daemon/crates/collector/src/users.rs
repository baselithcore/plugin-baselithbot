//! Local user / group / sudoers inventory.
//!
//! Linux: parses `/etc/passwd`, `/etc/group`, and the presence (with
//! sha256) of `/etc/sudoers` plus `/etc/sudoers.d/*`. Shadow files are
//! deliberately not read — secret material never crosses the wire.
//!
//! macOS: parses `/etc/passwd` for system users and shells out to
//! `dscl . -list /Users` for the directory-services view (Open
//! Directory replaces the local-only file model).
//!
//! Wire kind: `host.user.snapshot`. Schema:
//! ```text
//! {
//!   schema_version: 1,
//!   users: [{name, uid, gid, gecos, home, shell, login_enabled}],
//!   groups: [{name, gid, members}],
//!   sudoers: [{path, sha256, size_bytes}],
//!   source: "etc_passwd" | "dscl",
//! }
//! ```

use baselith_redagent_proto as proto;
use serde_json::{json, Value};

use crate::{build_event, hash::hash_file, mitre};

const SCHEMA_VERSION: u32 = 1;
/// Shells that mean "interactive login disabled". Used to surface
/// only the accounts an attacker could realistically log in as.
const NOLOGIN_SHELLS: &[&str] = &[
    "/usr/sbin/nologin",
    "/sbin/nologin",
    "/bin/false",
    "/usr/bin/false",
    "/dev/null",
];

/// Capture local users, groups, and sudoers metadata.
pub fn snapshot(severity: proto::Severity) -> proto::TelemetryEvent {
    let users = parse_passwd();
    let groups = parse_group();
    let sudoers = sudoers_metadata();
    let attrs = json!({
        "schema_version": SCHEMA_VERSION,
        "users": users,
        "groups": groups,
        "sudoers": sudoers,
        "source": "etc_passwd",
        "mitre_technique": mitre::USERS_LOCAL_ACCOUNTS,
    });
    build_event("host.user.snapshot", severity, attrs)
}

fn parse_passwd() -> Vec<Value> {
    let Ok(text) = std::fs::read_to_string("/etc/passwd") else {
        return Vec::new();
    };
    text.lines()
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .filter_map(|line| {
            let parts: Vec<&str> = line.split(':').collect();
            if parts.len() < 7 {
                return None;
            }
            let shell = parts[6];
            Some(json!({
                "name": parts[0],
                "uid": parts[2].parse::<u32>().unwrap_or(u32::MAX),
                "gid": parts[3].parse::<u32>().unwrap_or(u32::MAX),
                "gecos": parts[4],
                "home": parts[5],
                "shell": shell,
                "login_enabled": !NOLOGIN_SHELLS.contains(&shell),
            }))
        })
        .collect()
}

fn parse_group() -> Vec<Value> {
    let Ok(text) = std::fs::read_to_string("/etc/group") else {
        return Vec::new();
    };
    text.lines()
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .filter_map(|line| {
            let parts: Vec<&str> = line.split(':').collect();
            if parts.len() < 4 {
                return None;
            }
            let members: Vec<&str> = parts[3].split(',').filter(|s| !s.is_empty()).collect();
            Some(json!({
                "name": parts[0],
                "gid": parts[2].parse::<u32>().unwrap_or(u32::MAX),
                "members": members,
            }))
        })
        .collect()
}

fn sudoers_metadata() -> Vec<Value> {
    let mut out = Vec::new();
    let main = std::path::Path::new("/etc/sudoers");
    if main.exists() {
        out.push(file_metadata(main));
    }
    if let Ok(entries) = std::fs::read_dir("/etc/sudoers.d") {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                out.push(file_metadata(&path));
            }
        }
    }
    out
}

fn file_metadata(path: &std::path::Path) -> Value {
    let digest = hash_file(path);
    json!({
        "path": digest.path,
        "sha256": digest.sha256,
        "size_bytes": digest.size_bytes,
        "error_code": digest.error_code,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_emits_event_with_kind() {
        let evt = snapshot(proto::Severity::Info);
        assert_eq!(evt.kind, "host.user.snapshot");
        assert!(evt.attributes.is_some());
    }
}
