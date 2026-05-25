//! Daemon runtime configuration.
//!
//! Loaded from a TOML file on disk and overridden by environment
//! variables at the boundaries that vary per deployment (proxy URL,
//! log level). Identity material (cert / private key) lives in the OS
//! keystore — never in the config file.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::Path;

/// Top-level daemon configuration.
///
/// `keystore_id`, `https_proxy`, and `telemetry_buffer_path` are
/// parsed but consumed by the keystore / transport-proxy / offline-buffer
/// crates that land in the next milestone. The `allow(dead_code)`
/// attribute is removed once they're wired.
#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct Config {
    /// gRPC endpoint of the backend `AgentChannel` service.
    pub backend_endpoint: String,

    /// Protocol version this daemon will advertise in `AgentHello`.
    pub protocol_version: u32,

    /// Path to the persisted root CA fingerprint (pinned at install).
    pub root_ca_fingerprint_path: String,

    /// OS keystore identifier under which cert + key are stored.
    pub keystore_id: String,

    /// Optional outbound proxy. Honors HTTP CONNECT semantics.
    #[serde(default)]
    pub https_proxy: Option<String>,

    /// Local SQLite path for offline telemetry buffering.
    pub telemetry_buffer_path: String,
}

impl Config {
    /// Load and validate the configuration from `path`.
    pub fn load(path: &str) -> Result<Self> {
        let bytes = std::fs::read_to_string(Path::new(path))
            .with_context(|| format!("reading config from {path}"))?;
        let config: Config =
            toml::from_str(&bytes).with_context(|| format!("parsing config at {path}"))?;
        config.validate()?;
        Ok(config)
    }

    fn validate(&self) -> Result<()> {
        if self.backend_endpoint.is_empty() {
            anyhow::bail!("backend_endpoint must be set");
        }
        if self.protocol_version == 0 {
            anyhow::bail!("protocol_version must be ≥ 1");
        }
        Ok(())
    }
}
