//! BaselithCore Red Agent endpoint daemon — binary entrypoint.
//!
//! Phase 1 lifecycle:
//!
//! 1. Parse CLI / env config (`Config::load`).
//! 2. Initialize structured logging (`init_tracing`).
//! 3. Load identity material from the OS keystore (cert + private key)
//!    via the `keystore` crate. Bail early with a clear message if
//!    the daemon has not been enrolled yet.
//! 4. Build the mTLS gRPC transport (`transport::Client::connect`).
//! 5. Spawn the collector pump (`collector::run`) and the executor
//!    listener (`executor::run`) on the shared tokio runtime.
//! 6. Drive the bidirectional stream: send `AgentHello`, then loop
//!    over server messages, dispatching commands and acknowledging
//!    heartbeats.
//!
//! On graceful shutdown (`SIGTERM` / `SIGINT`) the daemon sends a
//! `DisconnectNotice{REASON_SHUTDOWN}` so the backend marks the
//! agent as "offline expected" rather than "lost".

#![deny(unsafe_code)]
#![warn(missing_docs)]

use std::sync::Arc;

use anyhow::{Context, Result};
use baselith_redagent_keystore::{pick_default_backend, Keystore, KeystoreId};
use baselith_redagent_policy::BundleVerifier;
use baselith_redagent_proto::AgentCapability;
use baselith_redagent_transport::{ClientConfig, Identity};
use clap::Parser;
use parking_lot::Mutex;
use tracing::{info, warn};
use uuid::Uuid;
use zeroize::Zeroizing;

mod cert_lifecycle;
mod config;
mod csr;
mod dispatch;
mod enroll;
mod health;
mod log_drain;
mod offline_buffer;
mod platform;
mod rotation;
mod runtime;
mod wire;

use config::Config;
use platform::PlatformInfo;
use runtime::DaemonIdentity;

const DAEMON_VERSION: &str = env!("CARGO_PKG_VERSION");

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let log_drain = init_tracing(&cli.verbose);

    let config = Config::load(&cli.config_path)?;
    info!(
        backend = %config.backend_endpoint,
        protocol_version = config.protocol_version,
        command = ?cli.command,
        "baselith-redagent-daemon starting"
    );

    match cli.command {
        Some(Command::Enroll { token, endpoint }) => {
            let _ = log_drain;
            let keystore = open_keystore(&config)?;
            let endpoint =
                endpoint.unwrap_or_else(|| derive_enroll_endpoint(&config.backend_endpoint));
            let token = Zeroizing::new(token);
            enroll::run(&config, token, &*keystore, DAEMON_VERSION, &endpoint).await?;
            Ok(())
        }
        None | Some(Command::Run) => run_daemon(&config, log_drain).await,
    }
}

async fn run_daemon(config: &Config, log_drain: log_drain::LogDrain) -> Result<()> {
    let platform = PlatformInfo::probe();
    let identity = DaemonIdentity {
        agent_uuid: Uuid::new_v4().to_string(),
        daemon_version: DAEMON_VERSION.to_string(),
        protocol_version: config.protocol_version,
        declared_capabilities: declared_capabilities(),
    };

    let keystore: std::sync::Arc<dyn Keystore> = open_keystore(config)?.into();
    info!(backend = keystore.backend_name(), "keystore opened");
    let keystore_id = KeystoreId(config.keystore_id.clone());

    let identity_material = keystore
        .load(&keystore_id)
        .with_context(|| "no enrolled identity; run `baselith-redagent-daemon enroll` first")?;

    let client_config = ClientConfig {
        endpoint: config.backend_endpoint.clone(),
        pinned_root_ca_fingerprint_sha256: read_pinned_fingerprint(config)?,
        identity: Identity {
            cert_chain_pem: identity_material.cert_chain_pem.to_vec(),
            private_key_pem: identity_material.private_key_pem.to_vec(),
        },
    };
    drop(identity_material);

    let verifier = load_policy_verifier(config)?;

    let buffer_path = std::path::PathBuf::from(&config.telemetry_buffer_path);
    let cert_pem_for_lifecycle = client_config.identity.cert_chain_pem.clone();
    let spool = match offline_buffer::Spool::open(
        &buffer_path,
        offline_buffer::DEFAULT_MAX_ROWS,
        offline_buffer::DEFAULT_MAX_BYTES,
    ) {
        Ok(s) => Some(std::sync::Arc::new(s)),
        Err(e) => {
            warn!(error = %e, path = %buffer_path.display(), "offline spool unavailable; running without persistence");
            None
        }
    };
    tokio::select! {
        _ = runtime::run_forever(
            client_config,
            identity,
            platform,
            verifier,
            buffer_path,
            log_drain,
            cert_pem_for_lifecycle,
            spool,
            keystore,
            keystore_id,
        ) => {
            unreachable!("run_forever returns Never");
        }
        _ = tokio::signal::ctrl_c() => {
            info!("baselith-redagent-daemon stopping (SIGINT)");
        }
    }
    Ok(())
}

fn load_policy_verifier(config: &Config) -> Result<Arc<Mutex<BundleVerifier>>> {
    // Phase 1: the policy public key path is convention-driven from
    // the fingerprint path's directory (`policy.pub`). Operators who
    // do not yet provision a key fall back to a verifier that rejects
    // every bundle, which is exactly the desired safe default.
    let fp_path = std::path::PathBuf::from(&config.root_ca_fingerprint_path);
    let dir = fp_path.parent().unwrap_or(std::path::Path::new("."));
    let key_path = dir.join("policy.pub");
    let bytes = match std::fs::read(&key_path) {
        Ok(b) => b,
        Err(e) => {
            warn!(
                error = %e,
                path = %key_path.display(),
                "policy public key not found; bundle verifier will refuse all updates"
            );
            // Construct an unconditionally-failing verifier by feeding
            // a synthetic key with `current_version = u64::MAX`. Any
            // incoming bundle will be Stale.
            let fake = [0u8; 32];
            let v = BundleVerifier::from_public_key_bytes(&fake, u64::MAX)
                .context("synthesise placeholder verifier")?;
            return Ok(Arc::new(Mutex::new(v)));
        }
    };
    let key = if bytes.len() == 32 {
        bytes
    } else {
        // Accept hex-encoded keys for operator convenience.
        let trimmed = String::from_utf8_lossy(&bytes).trim().to_string();
        hex::decode(&trimmed)
            .with_context(|| format!("decode hex policy key from {}", key_path.display()))?
    };
    let verifier = BundleVerifier::from_public_key_bytes(&key, 0)
        .with_context(|| format!("policy verifier from {}", key_path.display()))?;
    info!(path = %key_path.display(), "policy verifier loaded");
    Ok(Arc::new(Mutex::new(verifier)))
}

fn derive_enroll_endpoint(grpc_endpoint: &str) -> String {
    // Convention: REST enroll endpoint is the same host as the gRPC
    // backend, on port 443, path `/red-agent/agents/enroll`. Operators
    // can override via `--endpoint` when the layout differs.
    let trimmed = grpc_endpoint
        .trim_end_matches(":443")
        .trim_end_matches(":50443");
    format!("{trimmed}/red-agent/agents/enroll")
}

fn declared_capabilities() -> Vec<AgentCapability> {
    // Phase 1: inventory + on-demand hashing + sandboxed local
    // scanners. eBPF / ESF tracepoint capabilities land alongside the
    // runtime-tracer implementation in Phase 2.
    let mut caps = vec![
        AgentCapability::CapabilityProcInventory,
        AgentCapability::CapabilityPkgInventory,
        AgentCapability::CapabilityFileHash,
        AgentCapability::CapabilityNetListen,
        AgentCapability::CapabilityUserInventory,
        AgentCapability::CapabilityScanLocalTrivy,
        AgentCapability::CapabilityScanLocalNuclei,
        AgentCapability::CapabilityScanLocalSecrets,
    ];
    if cfg!(target_os = "linux") {
        caps.push(AgentCapability::CapabilitySandboxLandlock);
        caps.push(AgentCapability::CapabilitySandboxSeccomp);
    }
    if cfg!(target_os = "macos") {
        caps.push(AgentCapability::CapabilitySandboxSbxExec);
    }
    caps
}

fn read_pinned_fingerprint(config: &Config) -> Result<String> {
    std::fs::read_to_string(&config.root_ca_fingerprint_path)
        .map(|s| s.trim().to_lowercase())
        .with_context(|| {
            format!(
                "reading pinned root CA fingerprint from {}",
                config.root_ca_fingerprint_path
            )
        })
}

fn open_keystore(config: &Config) -> Result<Box<dyn Keystore>> {
    // Master secret derivation: bind the encrypted-file fallback to a
    // host-stable value (boot_id on linux, kern.bootsessionuuid on
    // macOS, hostname elsewhere) so the encrypted blob is bound to
    // the host and cannot be migrated to a sibling machine. This is
    // a Phase-1 simplification; Phase 2 swaps in TPM-sealed bytes.
    let host_bound = host_bound_secret();
    if host_bound.is_empty() {
        warn!("host-bound master secret empty; encrypted file backend will be weak");
    }
    let secret = Zeroizing::new(host_bound.into_bytes());
    let path = std::path::PathBuf::from(&config.telemetry_buffer_path)
        .parent()
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| std::path::PathBuf::from("/var/lib/baselith"));
    Ok(pick_default_backend(path, secret))
}

#[cfg(target_os = "linux")]
fn host_bound_secret() -> String {
    std::fs::read_to_string("/proc/sys/kernel/random/boot_id")
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}

#[cfg(target_os = "macos")]
fn host_bound_secret() -> String {
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
fn host_bound_secret() -> String {
    sysinfo::System::host_name().unwrap_or_default()
}

#[derive(Parser, Debug)]
#[command(version, about = "BaselithCore Red Agent endpoint daemon")]
struct Cli {
    /// Path to the daemon config file.
    #[arg(
        long,
        env = "BASELITH_REDAGENT_CONFIG",
        default_value = "/etc/baselith/redagent.toml"
    )]
    config_path: String,

    /// Increase log verbosity. Repeat for more detail.
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,

    #[command(subcommand)]
    command: Option<Command>,
}

#[derive(clap::Subcommand, Debug)]
enum Command {
    /// Run the daemon (default when no subcommand is given).
    Run,

    /// Redeem an enrollment token, persist the resulting identity to
    /// the keystore, and exit.
    Enroll {
        /// One-shot enrollment token issued by the operator.
        #[arg(long, env = "BASELITH_REDAGENT_TOKEN")]
        token: String,

        /// Override the REST endpoint URL; defaults to deriving it
        /// from the gRPC backend in the config file.
        #[arg(long)]
        endpoint: Option<String>,
    },
}

fn init_tracing(verbose: &u8) -> log_drain::LogDrain {
    use tracing_subscriber::layer::SubscriberExt;
    use tracing_subscriber::util::SubscriberInitExt;
    use tracing_subscriber::EnvFilter;

    let level = match verbose {
        0 => "info",
        1 => "debug",
        _ => "trace",
    };
    let env_filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(level));
    let (log_layer, drain) = log_drain::build();
    let fmt_layer = tracing_subscriber::fmt::layer().json();
    tracing_subscriber::registry()
        .with(env_filter)
        .with(fmt_layer)
        .with(log_layer)
        .init();
    drain
}
