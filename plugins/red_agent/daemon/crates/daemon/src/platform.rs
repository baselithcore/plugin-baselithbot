//! Platform metadata captured once at daemon startup.
//!
//! Sent inside the first `AgentHello` so the backend can populate
//! `red_agent_agents.os / kernel_version / arch / cpu_count / mem_total`.
//! Re-emitted on every reconnect because hosts can have hardware
//! changes between sessions (e.g. cloud VM resize).

use baselith_redagent_proto as proto;
use sysinfo::System;

/// Snapshot of host platform attributes.
#[derive(Debug, Clone)]
pub struct PlatformInfo {
    pub os: proto::v1::platform::Os,
    pub os_version: String,
    pub kernel_version: String,
    pub arch: String,
    pub hostname: String,
    pub cpu_count: u64,
    pub mem_total_bytes: u64,
    pub boot_id: String,
}

impl PlatformInfo {
    /// Probe the host using `sysinfo` and OS-specific fallbacks.
    pub fn probe() -> Self {
        let mut sys = System::new();
        sys.refresh_all();

        let os = if cfg!(target_os = "linux") {
            proto::v1::platform::Os::Linux
        } else if cfg!(target_os = "macos") {
            proto::v1::platform::Os::Macos
        } else if cfg!(target_os = "windows") {
            proto::v1::platform::Os::Windows
        } else {
            proto::v1::platform::Os::Unspecified
        };

        let arch = std::env::consts::ARCH.to_string();
        let hostname = System::host_name().unwrap_or_else(|| "unknown".to_string());
        let kernel_version = System::kernel_version().unwrap_or_default();
        let os_version = System::long_os_version().unwrap_or_default();
        let cpu_count = sys.cpus().len() as u64;
        let mem_total_bytes = sys.total_memory();
        let boot_id = boot_id_or_empty();

        Self {
            os,
            os_version,
            kernel_version,
            arch,
            hostname,
            cpu_count,
            mem_total_bytes,
            boot_id,
        }
    }

    /// Convert to the wire `Platform` message.
    pub fn to_proto(&self) -> proto::Platform {
        proto::Platform {
            os: self.os as i32,
            os_version: self.os_version.clone(),
            kernel_version: self.kernel_version.clone(),
            arch: self.arch.clone(),
            hostname: self.hostname.clone(),
            boot_id: self.boot_id.clone(),
            cpu_count: self.cpu_count,
            mem_total_bytes: self.mem_total_bytes,
        }
    }
}

#[cfg(target_os = "linux")]
fn boot_id_or_empty() -> String {
    std::fs::read_to_string("/proc/sys/kernel/random/boot_id")
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}

#[cfg(target_os = "macos")]
fn boot_id_or_empty() -> String {
    use std::process::Command;
    Command::new("sysctl")
        .args(["-n", "kern.bootsessionuuid"])
        .output()
        .ok()
        .and_then(|out| String::from_utf8(out.stdout).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn boot_id_or_empty() -> String {
    String::new()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn probe_returns_non_empty_basic_fields() {
        let info = PlatformInfo::probe();
        assert!(!info.arch.is_empty());
        assert!(info.cpu_count > 0);
    }

    #[test]
    fn to_proto_round_trips_fields() {
        let info = PlatformInfo::probe();
        let p = info.to_proto();
        assert_eq!(p.arch, info.arch);
        assert_eq!(p.cpu_count, info.cpu_count);
        assert_eq!(p.os, info.os as i32);
    }
}
