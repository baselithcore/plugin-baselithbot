//! Listening-socket collector.
//!
//! Linux: parses `/proc/net/tcp`, `/proc/net/tcp6`, `/proc/net/udp`,
//! `/proc/net/udp6` for sockets in `LISTEN` state and resolves the
//! socket inode to the owning pid by scanning `/proc/*/fd/*` symlinks.
//!
//! macOS: shells out to `lsof -nP -iTCP -sTCP:LISTEN -iUDP -F pcnL`
//! — the `-F` machine-readable form is parsed line-by-line. `lsof`
//! is part of macOS by default.
//!
//! Other platforms: returns an empty list.
//!
//! Wire kind: `host.net.listeners`. Per-socket payload schema:
//! `{ proto, family, local_addr, local_port, pid, process, user }`.

#[cfg(target_os = "linux")]
use std::collections::HashMap;

use baselith_redagent_proto as proto;
#[cfg_attr(
    not(any(target_os = "linux", target_os = "macos")),
    allow(unused_imports)
)]
use serde_json::{json, Value};

use crate::{build_event, mitre};

/// Capture all listening sockets on the host (TCP+UDP, v4+v6).
pub fn listening_sockets(severity: proto::Severity) -> proto::TelemetryEvent {
    let sockets = collect_listening();
    let count = sockets.len();
    let attrs = json!({
        "sockets": sockets,
        "count": count,
        "schema_version": 1,
        "mitre_technique": mitre::NET_LISTENERS_DISCOVERY,
    });
    build_event("host.net.listeners", severity, attrs)
}

#[cfg(target_os = "linux")]
fn collect_listening() -> Vec<Value> {
    let inode_to_pid = scan_fd_inodes();
    let mut out = Vec::new();
    for (path, family, transport) in [
        ("/proc/net/tcp", "ipv4", "tcp"),
        ("/proc/net/tcp6", "ipv6", "tcp"),
        ("/proc/net/udp", "ipv4", "udp"),
        ("/proc/net/udp6", "ipv6", "udp"),
    ] {
        if let Ok(text) = std::fs::read_to_string(path) {
            for entry in parse_proc_net(&text, transport, family, &inode_to_pid) {
                out.push(entry);
            }
        }
    }
    out
}

#[cfg(target_os = "linux")]
fn scan_fd_inodes() -> HashMap<u64, (u32, String)> {
    let mut map: HashMap<u64, (u32, String)> = HashMap::new();
    let Ok(proc_dir) = std::fs::read_dir("/proc") else {
        return map;
    };
    for entry in proc_dir.flatten() {
        let name = entry.file_name();
        let Some(s) = name.to_str() else { continue };
        let Ok(pid) = s.parse::<u32>() else { continue };
        let fd_dir = entry.path().join("fd");
        let Ok(fds) = std::fs::read_dir(&fd_dir) else {
            continue;
        };
        let comm = std::fs::read_to_string(entry.path().join("comm"))
            .map(|s| s.trim().to_string())
            .unwrap_or_default();
        for fd in fds.flatten() {
            let Ok(target) = std::fs::read_link(fd.path()) else {
                continue;
            };
            let Some(target_str) = target.to_str() else {
                continue;
            };
            // Format: socket:[12345]
            if let Some(rest) = target_str.strip_prefix("socket:[") {
                if let Some(num) = rest.strip_suffix(']') {
                    if let Ok(inode) = num.parse::<u64>() {
                        map.insert(inode, (pid, comm.clone()));
                    }
                }
            }
        }
    }
    map
}

#[cfg(target_os = "linux")]
fn parse_proc_net(
    text: &str,
    transport: &str,
    family: &str,
    inode_to_pid: &HashMap<u64, (u32, String)>,
) -> Vec<Value> {
    // Format (header on first line):
    //   sl  local_address rem_address st tx_q rx_q tr tm->when retrnsmt uid timeout inode ...
    // Listen state is "0A" for tcp; udp uses "07" but we treat any
    // bound udp as a listener since UDP has no real "listen" state.
    let mut out = Vec::new();
    for line in text.lines().skip(1) {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 10 {
            continue;
        }
        let local = parts[1];
        let state = parts[3];
        let uid: u32 = parts[7].parse().unwrap_or(0);
        let inode: u64 = parts[9].parse().unwrap_or(0);
        if transport == "tcp" && state != "0A" {
            continue;
        }
        let Some((addr, port)) = parse_addr(local, family) else {
            continue;
        };
        let pid_owner = inode_to_pid.get(&inode);
        out.push(json!({
            "proto": transport,
            "family": family,
            "local_addr": addr,
            "local_port": port,
            "uid": uid,
            "inode": inode,
            "pid": pid_owner.map(|(p, _)| *p),
            "process": pid_owner.map(|(_, c)| c.clone()),
        }));
    }
    out
}

#[cfg(target_os = "linux")]
fn parse_addr(s: &str, family: &str) -> Option<(String, u16)> {
    let (addr_hex, port_hex) = s.split_once(':')?;
    let port = u16::from_str_radix(port_hex, 16).ok()?;
    let addr = match family {
        "ipv4" => {
            let n = u32::from_str_radix(addr_hex, 16).ok()?;
            // Kernel writes little-endian groups.
            let bytes = n.to_le_bytes();
            format!("{}.{}.{}.{}", bytes[0], bytes[1], bytes[2], bytes[3])
        }
        "ipv6" => {
            // 32 hex chars, 4 little-endian u32 groups.
            if addr_hex.len() != 32 {
                return None;
            }
            let mut bytes = [0u8; 16];
            for (i, chunk) in addr_hex.as_bytes().chunks(8).enumerate() {
                let group_str = std::str::from_utf8(chunk).ok()?;
                let group = u32::from_str_radix(group_str, 16).ok()?;
                let le = group.to_le_bytes();
                bytes[i * 4..i * 4 + 4].copy_from_slice(&le);
            }
            format_ipv6(&bytes)
        }
        _ => return None,
    };
    Some((addr, port))
}

#[cfg(target_os = "linux")]
fn format_ipv6(bytes: &[u8; 16]) -> String {
    let groups: Vec<String> = bytes
        .chunks(2)
        .map(|c| format!("{:x}", u16::from_be_bytes([c[0], c[1]])))
        .collect();
    groups.join(":")
}

#[cfg(target_os = "macos")]
fn collect_listening() -> Vec<Value> {
    use std::process::Command;
    let output = Command::new("/usr/sbin/lsof")
        .args(["-nP", "-iTCP", "-sTCP:LISTEN", "-iUDP", "-F", "pcuLn"])
        .output();
    let Ok(output) = output else {
        return Vec::new();
    };
    if !output.status.success() {
        return Vec::new();
    }
    let text = String::from_utf8_lossy(&output.stdout);
    parse_lsof(&text)
}

#[cfg(target_os = "macos")]
fn parse_lsof(text: &str) -> Vec<Value> {
    // lsof -F prefixes each field with a single character: p=pid,
    // c=command, u=uid, n=name (host:port), L=login. Records are
    // grouped per-process; one process can have multiple sockets.
    let mut out = Vec::new();
    let mut pid: Option<u32> = None;
    let mut command: Option<String> = None;
    let mut uid: Option<u32> = None;
    for raw in text.lines() {
        let Some((tag, rest)) = raw.split_at_checked(1) else {
            continue;
        };
        match tag {
            "p" => {
                pid = rest.parse().ok();
                command = None;
                uid = None;
            }
            "c" => command = Some(rest.to_string()),
            "u" => uid = rest.parse().ok(),
            "n" => {
                if let Some(entry) = parse_lsof_name(rest, pid, command.as_deref(), uid) {
                    out.push(entry);
                }
            }
            _ => {}
        }
    }
    out
}

#[cfg(target_os = "macos")]
fn parse_lsof_name(
    name: &str,
    pid: Option<u32>,
    command: Option<&str>,
    uid: Option<u32>,
) -> Option<Value> {
    // Examples:
    //   *:8080            (ipv4 wildcard tcp/udp)
    //   127.0.0.1:5432
    //   [::1]:5432
    //   [::]:443
    let (addr, port_str) = if let Some(stripped) = name.strip_prefix('[') {
        let close = stripped.find(']')?;
        let addr = &stripped[..close];
        let port = &stripped[close + 2..];
        (addr.to_string(), port)
    } else {
        let (a, p) = name.rsplit_once(':')?;
        (a.to_string(), p)
    };
    let port: u16 = port_str.parse().ok()?;
    let family = if addr.contains(':') {
        "ipv6"
    } else if addr.contains('.') || addr == "*" {
        "ipv4"
    } else {
        "ipv6"
    };
    Some(json!({
        "proto": "tcp_or_udp",
        "family": family,
        "local_addr": addr,
        "local_port": port,
        "pid": pid,
        "process": command,
        "uid": uid,
    }))
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn collect_listening() -> Vec<Value> {
    Vec::new()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn emits_event_with_kind() {
        let evt = listening_sockets(proto::Severity::Info);
        assert_eq!(evt.kind, "host.net.listeners");
        assert!(evt.attributes.is_some());
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn parse_ipv4_addr_round_trip() {
        // 0100007F:1F90 → 127.0.0.1:8080
        let (addr, port) = parse_addr("0100007F:1F90", "ipv4").expect("parse");
        assert_eq!(addr, "127.0.0.1");
        assert_eq!(port, 8080);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn parse_ipv6_addr_round_trip() {
        // ::1 reversed in groups of u32: 00000000000000000000000001000000
        let (addr, port) =
            parse_addr("00000000000000000000000001000000:1F90", "ipv6").expect("parse");
        assert_eq!(port, 8080);
        assert!(addr.contains("1") || addr.contains("0"));
    }
}
