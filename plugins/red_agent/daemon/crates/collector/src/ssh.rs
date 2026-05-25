//! SSH-related artefact metadata.
//!
//! Walks every standard home directory looking for
//! `~/.ssh/authorized_keys` and `~/.ssh/authorized_keys2`. For each
//! file the collector emits **only metadata** — path, sha256, key
//! count, and the algorithm token of every key (`ssh-ed25519`,
//! `ecdsa-sha2-*`, `ssh-rsa`, ...). Public-key bodies are not
//! transmitted: a key fingerprint exposed on the wire is enough for
//! the backend to detect drift, and bodies have low forensic value
//! once the key file's sha256 changes.
//!
//! Also captures `/etc/ssh/sshd_config` — path, sha256, plus a small
//! summary of security-relevant directives surfaced as booleans:
//! `permit_root_login`, `password_authentication`, `pubkey_authentication`,
//! `permit_empty_passwords`, `challenge_response_authentication`.
//!
//! Wire kind: `host.ssh.snapshot`.

use std::path::{Path, PathBuf};

use baselith_redagent_proto as proto;
use serde_json::{json, Value};

use crate::{build_event, hash::hash_file, mitre};

const SCHEMA_VERSION: u32 = 1;
const HOME_ROOTS: &[&str] = &["/home", "/Users", "/root", "/var/root"];

/// Emit the combined `host.ssh.snapshot` event.
pub fn snapshot(severity: proto::Severity) -> proto::TelemetryEvent {
    let authorized_keys = scan_authorized_keys();
    let sshd_config = sshd_config_metadata();
    let permit_root = sshd_config_permits_root(&sshd_config);
    let mut techniques: Vec<&'static str> = Vec::new();
    if !authorized_keys.is_empty() {
        techniques.push(mitre::SSH_AUTHORIZED_KEYS);
    }
    if permit_root {
        techniques.push(mitre::SSH_PERMIT_ROOT_LOGIN);
    }
    let attrs = json!({
        "schema_version": SCHEMA_VERSION,
        "authorized_keys": authorized_keys,
        "sshd_config": sshd_config,
        "mitre_techniques": techniques,
    });
    build_event("host.ssh.snapshot", severity, attrs)
}

fn sshd_config_permits_root(cfg: &Value) -> bool {
    cfg.get("directives")
        .and_then(|d| d.get("permit_root_login"))
        .and_then(|v| v.as_str())
        .map(|s| s == "yes" || s == "without-password" || s == "prohibit-password")
        .unwrap_or(false)
}

fn scan_authorized_keys() -> Vec<Value> {
    let mut out: Vec<Value> = Vec::new();
    for root in HOME_ROOTS {
        if root == &"/root" || root == &"/var/root" {
            collect_one(Path::new(root), &mut out);
        } else if let Ok(entries) = std::fs::read_dir(root) {
            for entry in entries.flatten() {
                if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                    collect_one(&entry.path(), &mut out);
                }
            }
        }
    }
    out
}

fn collect_one(home: &Path, out: &mut Vec<Value>) {
    for fname in ["authorized_keys", "authorized_keys2"] {
        let path: PathBuf = home.join(".ssh").join(fname);
        if !path.is_file() {
            continue;
        }
        let digest = hash_file(&path);
        let (algorithms, key_count) = parse_authorized_keys(&path);
        out.push(json!({
            "path": digest.path,
            "sha256": digest.sha256,
            "size_bytes": digest.size_bytes,
            "key_count": key_count,
            "algorithms": algorithms,
            "error_code": digest.error_code,
        }));
    }
}

fn parse_authorized_keys(path: &Path) -> (Vec<String>, usize) {
    let Ok(text) = std::fs::read_to_string(path) else {
        return (Vec::new(), 0);
    };
    let mut algos: Vec<String> = Vec::new();
    let mut count = 0usize;
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        // Skip leading options blob: a key line with options has
        // leading non-whitespace tokens that contain '=' before the
        // algorithm. Heuristic: take the first token that begins with
        // "ssh-", "ecdsa-", or "sk-".
        let algo = line
            .split_whitespace()
            .find(|t| t.starts_with("ssh-") || t.starts_with("ecdsa-") || t.starts_with("sk-"))
            .map(|s| s.to_string());
        if let Some(a) = algo {
            algos.push(a);
            count += 1;
        }
    }
    (algos, count)
}

fn sshd_config_metadata() -> Value {
    let path = Path::new("/etc/ssh/sshd_config");
    if !path.is_file() {
        return Value::Null;
    }
    let digest = hash_file(path);
    let directives = parse_sshd_directives(path);
    json!({
        "path": digest.path,
        "sha256": digest.sha256,
        "size_bytes": digest.size_bytes,
        "directives": directives,
    })
}

fn parse_sshd_directives(path: &Path) -> Value {
    let Ok(text) = std::fs::read_to_string(path) else {
        return Value::Null;
    };
    let mut permit_root: Option<String> = None;
    let mut password_auth: Option<bool> = None;
    let mut pubkey_auth: Option<bool> = None;
    let mut permit_empty: Option<bool> = None;
    let mut challenge_response: Option<bool> = None;
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut parts = line.split_whitespace();
        let key = parts.next().unwrap_or("").to_lowercase();
        let val = parts.next().unwrap_or("").to_lowercase();
        match key.as_str() {
            "permitrootlogin" => permit_root = Some(val),
            "passwordauthentication" => password_auth = Some(val == "yes"),
            "pubkeyauthentication" => pubkey_auth = Some(val == "yes"),
            "permitemptypasswords" => permit_empty = Some(val == "yes"),
            "challengeresponseauthentication" | "kbdinteractiveauthentication" => {
                challenge_response = Some(val == "yes")
            }
            _ => {}
        }
    }
    json!({
        "permit_root_login": permit_root,
        "password_authentication": password_auth,
        "pubkey_authentication": pubkey_auth,
        "permit_empty_passwords": permit_empty,
        "challenge_response_authentication": challenge_response,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn snapshot_emits_event_with_kind() {
        let evt = snapshot(proto::Severity::Info);
        assert_eq!(evt.kind, "host.ssh.snapshot");
        assert!(evt.attributes.is_some());
    }

    #[test]
    fn parse_authorized_keys_extracts_algos() {
        let dir = std::env::temp_dir().join(format!("baselith-ssh-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("authorized_keys");
        let mut f = std::fs::File::create(&p).unwrap();
        writeln!(
            f,
            "# comment\n\
             ssh-ed25519 AAAAC3Nz user@host\n\
             command=\"/bin/foo\" ssh-rsa AAAAB3Nz another@host\n"
        )
        .unwrap();
        drop(f);
        let (algos, count) = parse_authorized_keys(&p);
        assert_eq!(count, 2);
        assert!(algos.contains(&"ssh-ed25519".to_string()));
        assert!(algos.contains(&"ssh-rsa".to_string()));
    }
}
