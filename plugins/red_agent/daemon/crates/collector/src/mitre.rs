//! MITRE ATT&CK technique mapping for telemetry events.
//!
//! Each collector emits stable wire kinds; this module turns the
//! kind (and per-entry fingerprints) into the canonical technique IDs
//! the backend's red-agent planner consumes. Mapping intentionally
//! errs on the side of breadth — false positives at the daemon are
//! cheaper than missed coverage.
//!
//! References: https://attack.mitre.org/ (Enterprise Matrix v15+).

/// Persistence-related technique IDs keyed by the `kind` field
/// emitted in [`crate::persistence`] entries.
pub fn persistence_technique(kind: &str) -> Option<&'static str> {
    Some(match kind {
        "cron.hourly" | "cron.daily" | "cron.weekly" | "cron.monthly" | "cron.d" | "crontabs"
        | "crontab" => "T1053.003",
        "systemd.etc" | "systemd.usrlib" | "systemd.lib" => "T1543.002",
        "init.d" => "T1037.004",
        "rc.local" => "T1037.004",
        "xdg.autostart" | "xdg.autostart.user" => "T1547.013",
        "LaunchDaemon" | "LaunchDaemon.system" => "T1543.004",
        "LaunchAgent" | "LaunchAgent.system" | "LaunchAgent.user" => "T1543.001",
        _ => return None,
    })
}

/// SSH-related techniques. Returns the canonical authorized_keys ID
/// for any matched key file; the backend decides severity from the
/// per-file metadata.
pub const SSH_AUTHORIZED_KEYS: &str = "T1098.004";
/// `PermitRootLogin yes` enables the valid-account technique.
pub const SSH_PERMIT_ROOT_LOGIN: &str = "T1078.003";

/// Local user enumeration.
pub const USERS_LOCAL_ACCOUNTS: &str = "T1087.001";

/// Kernel module loading (rootkit primitive).
pub const KERNEL_MODULES: &str = "T1547.006";

/// `LD_PRELOAD` / `DYLD_INSERT_LIBRARIES` injection vector.
pub const PRELOAD_INJECTION: &str = "T1574.006";

/// Local firewall configuration enumeration.
pub const FIREWALL_DISCOVERY: &str = "T1518.001";

/// Listening sockets discovery (network service enumeration).
pub const NET_LISTENERS_DISCOVERY: &str = "T1049";

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_persistence_kinds_map() {
        assert_eq!(persistence_technique("cron.daily"), Some("T1053.003"));
        assert_eq!(persistence_technique("systemd.etc"), Some("T1543.002"));
        assert_eq!(persistence_technique("LaunchAgent.user"), Some("T1543.001"));
    }

    #[test]
    fn unknown_kind_returns_none() {
        assert!(persistence_technique("unknown.kind").is_none());
    }
}
