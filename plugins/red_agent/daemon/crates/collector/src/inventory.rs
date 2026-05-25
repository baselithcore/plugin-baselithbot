//! Inventory collectors driven by `sysinfo`.
//!
//! Two on-demand sources:
//!
//! * [`processes`] — running processes with the fields a forensic
//!   reviewer expects (pid, ppid, exe, cmdline, uid/gid, rss/vsz,
//!   start_time, cwd, environ-shape).
//! * [`packages`] — installed packages (apt / rpm / brew).
//!
//! Listening sockets live in [`crate::net`].
//! On-demand file hashing lives in [`crate::hash`].
//!
//! All event payloads carry a `schema_version` field so the backend
//! parser can evolve without bumping the protocol version.

use std::process::Command;

use baselith_redagent_proto as proto;
use serde_json::{json, Value};
use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};

use crate::{build_event, mitre};

const PROCESS_SCHEMA_VERSION: u32 = 2;
const PACKAGE_SCHEMA_VERSION: u32 = 2;

/// Capture a one-shot process snapshot.
pub fn processes(severity: proto::Severity) -> proto::TelemetryEvent {
    let mut sys = System::new();
    sys.refresh_processes_specifics(
        ProcessesToUpdate::All,
        true,
        ProcessRefreshKind::new()
            .with_cmd(UpdateKind::Always)
            .with_cwd(UpdateKind::Always)
            .with_environ(UpdateKind::Always)
            .with_exe(UpdateKind::Always)
            .with_user(UpdateKind::Always)
            .with_memory()
            .with_cpu(),
    );

    let processes: Vec<Value> = sys
        .processes()
        .iter()
        .map(|(pid, p)| describe_process(*pid, p, &sys))
        .collect();

    let total = processes.len();
    let attrs = json!({
        "schema_version": PROCESS_SCHEMA_VERSION,
        "processes": processes,
        "total_count": total,
    });
    build_event("host.proc.snapshot", severity, attrs)
}

fn describe_process(pid: Pid, p: &sysinfo::Process, sys: &System) -> Value {
    let cmd: Vec<String> = p
        .cmd()
        .iter()
        .map(|s| s.to_string_lossy().into_owned())
        .collect();
    let environ_keys: Vec<String> = p
        .environ()
        .iter()
        .filter_map(|e| {
            let s = e.to_string_lossy();
            s.split_once('=').map(|(k, _)| k.to_string())
        })
        .collect();
    // Detection-relevant injection vectors: surface presence (not value)
    // of the canonical preload variables so the backend can flag them
    // without accepting raw env on the wire.
    let suspicious_env: Vec<&str> = ["LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"]
        .iter()
        .filter(|name| environ_keys.iter().any(|k| k == *name))
        .copied()
        .collect();
    let parent_pid = p.parent().map(|pp| pp.as_u32());
    let parent_name = parent_pid
        .and_then(|ppid| sys.process(Pid::from_u32(ppid)))
        .map(|pp| pp.name().to_string_lossy().into_owned());

    let preload_techniques: Vec<&'static str> = if !suspicious_env.is_empty() {
        vec![mitre::PRELOAD_INJECTION]
    } else {
        vec![]
    };
    json!({
        "pid": pid.as_u32(),
        "ppid": parent_pid,
        "parent_name": parent_name,
        "mitre_techniques": preload_techniques,
        "name": p.name().to_string_lossy(),
        "exe": p.exe().map(|p| p.to_string_lossy().into_owned()),
        "cwd": p.cwd().map(|p| p.to_string_lossy().into_owned()),
        "user_id": p.user_id().map(|u| u.to_string()),
        "effective_user_id": p.effective_user_id().map(|u| u.to_string()),
        "group_id": p.group_id().map(|g| g.to_string()),
        "effective_group_id": p.effective_group_id().map(|g| g.to_string()),
        "cmd": cmd,
        "start_time_unix": p.start_time(),
        "run_time_seconds": p.run_time(),
        "rss_bytes": p.memory(),
        "virtual_bytes": p.virtual_memory(),
        "cpu_percent": p.cpu_usage(),
        "status": format!("{:?}", p.status()),
        "session_id": p.session_id().map(|s| s.as_u32()),
        "thread_kind": format!("{:?}", p.thread_kind()),
        "environ_keys": environ_keys,
        "preload_env_present": suspicious_env,
    })
}

/// Capture installed packages from whichever package manager is
/// available. Phase 1 supports the operator's primary system manager;
/// language-specific package managers (pip, npm) are out of scope and
/// land alongside the executor's local SCA scanner.
pub fn packages(severity: proto::Severity) -> proto::TelemetryEvent {
    let (manager, packages) = detect_packages();
    let attrs = json!({
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "packages": packages,
        "manager": manager,
        "count": packages.len(),
    });
    build_event("host.pkg.snapshot", severity, attrs)
}

fn detect_packages() -> (&'static str, Vec<String>) {
    if cfg!(target_os = "linux") {
        if let Some(packages) = run_packages(&["dpkg-query", "-W", "-f=${Package}\t${Version}\n"]) {
            return ("dpkg", packages);
        }
        if let Some(packages) =
            run_packages(&["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\n"])
        {
            return ("rpm", packages);
        }
        if let Some(packages) = run_packages(&["pacman", "-Q"]) {
            return ("pacman", packages);
        }
    }
    if cfg!(target_os = "macos") {
        if let Some(packages) = run_packages(&["brew", "list", "--versions"]) {
            return ("brew", packages);
        }
    }
    ("unknown", Vec::new())
}

fn run_packages(argv: &[&str]) -> Option<Vec<String>> {
    let output = Command::new(argv[0]).args(&argv[1..]).output().ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let lines: Vec<String> = text
        .lines()
        .filter(|l| !l.is_empty())
        .map(|l| l.to_string())
        .collect();
    Some(lines)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn process_snapshot_has_kind() {
        let evt = processes(proto::Severity::Info);
        assert_eq!(evt.kind, "host.proc.snapshot");
        assert!(evt.attributes.is_some());
    }

    #[test]
    fn process_snapshot_carries_schema_version() {
        let evt = processes(proto::Severity::Info);
        let attrs = evt.attributes.expect("attrs");
        assert!(attrs.fields.contains_key("schema_version"));
        assert!(attrs.fields.contains_key("processes"));
    }

    #[test]
    fn package_snapshot_returns_known_manager() {
        let evt = packages(proto::Severity::Info);
        assert_eq!(evt.kind, "host.pkg.snapshot");
        let attrs = evt.attributes.expect("attrs");
        let manager = attrs.fields.get("manager").expect("manager field");
        match &manager.kind {
            Some(prost_types::value::Kind::StringValue(_)) => {}
            other => panic!("expected string, got {other:?}"),
        }
    }
}
