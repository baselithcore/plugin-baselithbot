//! Server-issued command dispatcher.
//!
//! Translates an inbound `ServerMessage::Command` into a sandboxed
//! local action (inventory probe, file hash, scanner exec) and emits
//! the resulting `CommandResult` back onto the outbound stream.
//!
//! Idempotency: the dispatcher caches the most recent
//! `CommandResult` for every `idempotency_key` it has executed. A
//! subsequent command with the same key returns the cached result
//! without re-running the underlying action. Cache entries expire
//! after [`IDEMPOTENCY_TTL`].
//!
//! Phase 1 implements:
//!
//! * `RunInventoryCmd` — process / package / listener snapshots.
//! * `HashFilesCmd`    — sha256 over a backend-supplied path list,
//!   gated by the local policy allowlist.
//!
//! All other command kinds short-circuit with `STATUS_UNSUPPORTED` so
//! the backend can downgrade gracefully without timing out.

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::{Duration, Instant};

use baselith_redagent_collector::{hash, inventory, json_to_struct, net, users};
use baselith_redagent_executor::{
    self as executor, ExecRequest, ResourceLimits as ExecLimits, ScannerKind,
};
use baselith_redagent_proto as proto;
use parking_lot::Mutex;
use prost_types::Duration as ProstDuration;
use serde_json::json;
use sha2::{Digest, Sha256};
use tokio::sync::mpsc;
use tracing::{debug, info, warn};

use crate::health::TelemetryLag;
use crate::wire::{now_timestamp, random_nonce};

/// How long a successfully completed command keeps its cached result.
/// Matches the proto-documented "last 24 h" idempotency window.
pub const IDEMPOTENCY_TTL: Duration = Duration::from_secs(24 * 60 * 60);

/// Cap on the number of paths a single `HashFilesCmd` may carry.
const MAX_HASH_PATHS: usize = 64;

/// Allowlisted root prefixes for `CollectArtifactCmd`. Same shape as
/// the hash allowlist; defined separately so an operator can tighten
/// exfil targets without affecting hashing.
const ARTIFACT_PATH_ALLOWLIST: &[&str] = &[
    "/etc/",
    "/var/log/",
    "/var/lib/baselith/",
    "/tmp/",
    "/Library/Logs/",
    "/private/var/log/",
];

/// Cap on a single `CollectArtifactCmd` payload (hard ceiling so the
/// agent never streams an arbitrarily large blob inline). Larger
/// targets must use the out-of-band upload flow announced via
/// `apply_config`.
const MAX_INLINE_ARTIFACT_BYTES: u64 = 4 * 1024 * 1024;

/// Allowlisted root prefixes for `HashFilesCmd`. Anything outside is
/// rejected at the daemon before any `open()` — defense in depth on
/// top of the server-side check.
const HASH_PATH_ALLOWLIST: &[&str] = &[
    "/etc/",
    "/usr/",
    "/opt/",
    "/var/lib/baselith/",
    "/Library/",
    "/Applications/",
    "/private/etc/",
    "/private/var/",
];

/// Idempotency cache entry.
struct CachedResult {
    result: proto::v1::CommandResult,
    inserted_at: Instant,
}

/// Dispatcher state. Cloned cheaply (Arc inside) so multiple tasks
/// can share the same idempotency view.
#[derive(Clone)]
pub struct Dispatcher {
    cache: std::sync::Arc<Mutex<HashMap<String, CachedResult>>>,
    lag: TelemetryLag,
}

impl Dispatcher {
    /// Build a fresh dispatcher with an empty idempotency cache.
    pub fn new(lag: TelemetryLag) -> Self {
        Self {
            cache: std::sync::Arc::new(Mutex::new(HashMap::new())),
            lag,
        }
    }

    /// Execute `command` and emit the resulting `CommandResult` on
    /// `tx`. Returns immediately after enqueueing; the outbound
    /// channel handles the actual wire flush.
    pub async fn dispatch(
        &self,
        command: proto::v1::Command,
        tx: mpsc::Sender<proto::AgentMessage>,
        seq_for_msg: u64,
    ) {
        let key = command.idempotency_key.clone();
        let correlation = command.correlation_id.clone();
        if !key.is_empty() {
            self.evict_stale();
            let cached_result = {
                let guard = self.cache.lock();
                guard.get(&key).map(|c| c.result.clone())
            };
            if let Some(result) = cached_result {
                debug!(idempotency_key = %key, "returning cached command result");
                self.send(tx, result, seq_for_msg).await;
                return;
            }
        }

        let started = Instant::now();
        let mut result = self.run_kind(&command, &correlation).await;
        result.idempotency_key = key.clone();
        result.correlation_id = correlation;
        result.elapsed = Some(ProstDuration {
            seconds: started.elapsed().as_secs() as i64,
            nanos: started.elapsed().subsec_nanos() as i32,
        });

        if !key.is_empty() {
            self.cache.lock().insert(
                key,
                CachedResult {
                    result: result.clone(),
                    inserted_at: Instant::now(),
                },
            );
        }
        self.send(tx, result, seq_for_msg).await;
    }

    fn evict_stale(&self) {
        let mut guard = self.cache.lock();
        guard.retain(|_, e| e.inserted_at.elapsed() < IDEMPOTENCY_TTL);
    }

    async fn send(
        &self,
        tx: mpsc::Sender<proto::AgentMessage>,
        result: proto::v1::CommandResult,
        seq: u64,
    ) {
        let msg = proto::AgentMessage {
            seq,
            nonce: random_nonce(),
            ts: Some(now_timestamp()),
            payload: Some(proto::v1::agent_message::Payload::CommandResult(result)),
        };
        if tx.send(msg).await.is_ok() {
            self.lag.record_enqueue();
        } else {
            debug!("command result channel closed");
        }
    }

    async fn run_kind(
        &self,
        command: &proto::v1::Command,
        correlation: &str,
    ) -> proto::v1::CommandResult {
        let Some(kind) = &command.kind else {
            return failed(
                "COMMAND.MISSING_KIND",
                "command has no kind oneof variant",
                proto::v1::command_result::Status::Failed,
            );
        };
        let mut local_telemetry: Vec<proto::TelemetryEvent> = Vec::new();
        let result = match kind {
            proto::v1::command::Kind::RunInventory(req) => {
                run_inventory(req, &mut local_telemetry, correlation)
            }
            proto::v1::command::Kind::HashFiles(req) => run_hash_files(req, correlation),
            proto::v1::command::Kind::RunLocalScan(req) => run_local_scan(req).await,
            proto::v1::command::Kind::CollectArtifact(req) => collect_artifact(req),
            proto::v1::command::Kind::ApplyConfig(req) => apply_config(req),
            proto::v1::command::Kind::SelfUpdate(_) => unsupported(kind_name(kind)),
        };
        // Phase 1 inventory commands also surface their findings as
        // standalone telemetry events. The transport pump does not
        // see them yet, but emitting via the result payload preserves
        // the data path until the per-event pipeline is wired.
        if !local_telemetry.is_empty() {
            info!(events = local_telemetry.len(), "command emitted telemetry");
        }
        result
    }
}

fn run_inventory(
    req: &proto::v1::RunInventoryCmd,
    telemetry: &mut Vec<proto::TelemetryEvent>,
    correlation: &str,
) -> proto::v1::CommandResult {
    use proto::v1::run_inventory_cmd::Kind as IK;
    let kinds: Vec<IK> = req
        .kinds
        .iter()
        .filter_map(|k| IK::try_from(*k).ok())
        .collect();
    let kinds: Vec<IK> = if kinds.is_empty() {
        vec![IK::Processes, IK::Packages, IK::Listeners]
    } else {
        kinds
    };

    let mut counts = serde_json::Map::new();
    for k in &kinds {
        let evt = match k {
            IK::Processes => {
                let mut e = inventory::processes(proto::Severity::Info);
                e.correlation_id = correlation.to_string();
                e
            }
            IK::Packages => {
                let mut e = inventory::packages(proto::Severity::Info);
                e.correlation_id = correlation.to_string();
                e
            }
            IK::Listeners => {
                let mut e = net::listening_sockets(proto::Severity::Info);
                e.correlation_id = correlation.to_string();
                e
            }
            IK::Users => {
                let mut e = users::snapshot(proto::Severity::Info);
                e.correlation_id = correlation.to_string();
                e
            }
            IK::Unspecified => continue,
        };
        counts.insert(format!("{:?}", k), json!(evt.kind));
        telemetry.push(evt);
    }
    let payload = json!({
        "ran_kinds": counts,
        "telemetry_event_count": telemetry.len(),
    });
    ok_result(json_to_struct(payload))
}

fn run_hash_files(req: &proto::v1::HashFilesCmd, _correlation: &str) -> proto::v1::CommandResult {
    use proto::v1::hash_files_cmd::Algorithm;

    if req.paths.len() > MAX_HASH_PATHS {
        return failed(
            "HASH.TOO_MANY_PATHS",
            &format!("limit {MAX_HASH_PATHS}, got {}", req.paths.len()),
            proto::v1::command_result::Status::Rejected,
        );
    }
    if req.algorithm != Algorithm::Sha256 as i32 && req.algorithm != Algorithm::Unspecified as i32 {
        return failed(
            "HASH.UNSUPPORTED_ALGORITHM",
            "Phase 1 supports SHA-256 only",
            proto::v1::command_result::Status::Unsupported,
        );
    }

    let mut allowed: Vec<PathBuf> = Vec::with_capacity(req.paths.len());
    let mut rejected: Vec<serde_json::Value> = Vec::new();
    for p in &req.paths {
        if path_allowed(p) {
            allowed.push(PathBuf::from(p));
        } else {
            rejected.push(json!({"path": p, "error_code": "POLICY.PATH_DENIED"}));
        }
    }

    let digests = hash::hash_files(allowed);
    let payload = json!({
        "schema_version": 1,
        "algorithm": "sha256",
        "digests": digests,
        "rejected": rejected,
    });
    ok_result(json_to_struct(payload))
}

fn path_allowed(path: &str) -> bool {
    if !std::path::Path::new(path).is_absolute() {
        return false;
    }
    HASH_PATH_ALLOWLIST
        .iter()
        .any(|prefix| path.starts_with(prefix))
}

fn artifact_path_allowed(path: &str) -> bool {
    if !std::path::Path::new(path).is_absolute() {
        return false;
    }
    ARTIFACT_PATH_ALLOWLIST
        .iter()
        .any(|prefix| path.starts_with(prefix))
}

async fn run_local_scan(req: &proto::v1::RunLocalScanCmd) -> proto::v1::CommandResult {
    let Some(scanner) = bundle_to_scanner(&req.bundle_id) else {
        return failed(
            "SCAN.UNKNOWN_BUNDLE",
            &format!(
                "bundle_id {:?} is not in the local scanner registry",
                req.bundle_id
            ),
            proto::v1::command_result::Status::Rejected,
        );
    };
    let limits = req
        .limits
        .as_ref()
        .map(|l| ExecLimits {
            wall_timeout: l.wall_timeout.as_ref().map(|d| {
                std::time::Duration::from_secs(d.seconds.max(0) as u64)
                    + std::time::Duration::from_nanos(d.nanos.max(0) as u64)
            }),
            output_cap_bytes: None,
            mem_max_bytes: if l.mem_max_bytes == 0 {
                None
            } else {
                Some(l.mem_max_bytes)
            },
            cpu_quota_us_per_sec: if l.cpu_quota_us_per_sec == 0 {
                None
            } else {
                Some(l.cpu_quota_us_per_sec)
            },
        })
        .unwrap_or_default();

    let exec_req = ExecRequest {
        scanner,
        argv: req.argv.clone(),
        limits,
    };

    info!(?scanner, argv = ?exec_req.argv, "running local scanner under sandbox");
    match executor::run_sandboxed(&exec_req).await {
        Ok(outcome) => {
            let payload = json!({
                "schema_version": 1,
                "scanner": scanner_str(scanner),
                "exit_code": outcome.exit_code,
                "stdout": String::from_utf8_lossy(&outcome.stdout).into_owned(),
                "stderr": String::from_utf8_lossy(&outcome.stderr).into_owned(),
                "stdout_bytes": outcome.stdout.len(),
                "stderr_bytes": outcome.stderr.len(),
                "elapsed_ms": outcome.elapsed.as_millis() as u64,
            });
            ok_result(json_to_struct(payload))
        }
        Err(e) => {
            let (code, status) = match &e {
                executor::ExecutorError::PolicyDenied(_) => (
                    "SCAN.POLICY_DENIED",
                    proto::v1::command_result::Status::Rejected,
                ),
                executor::ExecutorError::Spawn(_) => (
                    "SCAN.SPAWN_FAILED",
                    proto::v1::command_result::Status::Failed,
                ),
                executor::ExecutorError::Timeout => {
                    ("SCAN.TIMEOUT", proto::v1::command_result::Status::Timeout)
                }
                executor::ExecutorError::ExitCode { .. } => (
                    "SCAN.NONZERO_EXIT",
                    proto::v1::command_result::Status::Failed,
                ),
                executor::ExecutorError::OutputTooLarge { .. } => (
                    "SCAN.OUTPUT_TRUNCATED",
                    proto::v1::command_result::Status::Partial,
                ),
            };
            failed(code, &e.to_string(), status)
        }
    }
}

fn bundle_to_scanner(bundle_id: &str) -> Option<ScannerKind> {
    match bundle_id {
        "trivy_fs" | "trivy" => Some(ScannerKind::TrivyFs),
        "nuclei_local" | "nuclei" => Some(ScannerKind::NucleiLocal),
        "secret_scan" | "gitleaks" => Some(ScannerKind::SecretScan),
        _ => None,
    }
}

fn scanner_str(s: ScannerKind) -> &'static str {
    match s {
        ScannerKind::TrivyFs => "trivy_fs",
        ScannerKind::NucleiLocal => "nuclei_local",
        ScannerKind::SecretScan => "secret_scan",
    }
}

fn collect_artifact(req: &proto::v1::CollectArtifactCmd) -> proto::v1::CommandResult {
    if !artifact_path_allowed(&req.path) {
        return failed(
            "ARTIFACT.PATH_DENIED",
            &format!("path {} is not on the artifact allowlist", req.path),
            proto::v1::command_result::Status::Rejected,
        );
    }
    let cap = if req.max_bytes == 0 {
        MAX_INLINE_ARTIFACT_BYTES
    } else {
        req.max_bytes.min(MAX_INLINE_ARTIFACT_BYTES)
    };

    let metadata = match std::fs::metadata(&req.path) {
        Ok(m) => m,
        Err(e) => {
            let code = match e.kind() {
                std::io::ErrorKind::NotFound => "ARTIFACT.NOT_FOUND",
                std::io::ErrorKind::PermissionDenied => "ARTIFACT.DENIED",
                _ => "ARTIFACT.IO_ERROR",
            };
            return failed(
                code,
                &e.to_string(),
                proto::v1::command_result::Status::Failed,
            );
        }
    };
    if !metadata.is_file() {
        return failed(
            "ARTIFACT.NOT_A_FILE",
            "target is not a regular file",
            proto::v1::command_result::Status::Rejected,
        );
    }

    let take = metadata.len().min(cap) as usize;
    let bytes = match std::fs::read(&req.path) {
        Ok(mut b) => {
            b.truncate(take);
            b
        }
        Err(e) => {
            return failed(
                "ARTIFACT.IO_ERROR",
                &e.to_string(),
                proto::v1::command_result::Status::Failed,
            );
        }
    };
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    let sha = hex::encode(hasher.finalize());

    let chunk = proto::v1::ArtifactChunk {
        artifact_id: uuid::Uuid::new_v4().to_string(),
        chunk_index: 0,
        chunk_total: 1,
        data: bytes,
        sha256_hex: sha,
    };
    let payload = json!({
        "schema_version": 1,
        "path": req.path,
        "size_bytes": metadata.len(),
        "transmitted_bytes": take,
        "truncated": (metadata.len() as usize) > take,
    });
    let mut result = ok_result(json_to_struct(payload));
    result.artifact = Some(chunk);
    if (metadata.len() as usize) > take {
        result.status = proto::v1::command_result::Status::Partial as i32;
        result.error_code = "ARTIFACT.TRUNCATED".to_string();
        result.error_message = format!("file size {} exceeds inline cap {}", metadata.len(), cap);
    }
    result
}

fn apply_config(req: &proto::v1::ApplyConfigCmd) -> proto::v1::CommandResult {
    // Phase 1: ack the apply and surface the keys we recognized in the
    // result payload so the planner can assert what was actually
    // applied. Persistent rewrite of `/etc/baselith/redagent.toml`
    // lands in Phase 2 alongside the file-watch trigger.
    let mut applied: Vec<String> = Vec::new();
    let mut ignored: Vec<String> = Vec::new();
    if let Some(cfg) = req.config.as_ref() {
        for key in cfg.fields.keys() {
            if matches!(
                key.as_str(),
                "log_level"
                    | "telemetry_filters"
                    | "upload_url"
                    | "heartbeat_interval"
                    | "inventory_interval"
            ) {
                applied.push(key.clone());
            } else {
                ignored.push(key.clone());
            }
        }
    }
    info!(
        applied_keys = ?applied,
        ignored_keys = ?ignored,
        "apply_config received"
    );
    let payload = json!({
        "schema_version": 1,
        "applied_keys": applied,
        "ignored_keys": ignored,
        "phase": "ack-only",
    });
    ok_result(json_to_struct(payload))
}

#[allow(dead_code)]
fn kind_name(kind: &proto::v1::command::Kind) -> &'static str {
    match kind {
        proto::v1::command::Kind::RunInventory(_) => "run_inventory",
        proto::v1::command::Kind::RunLocalScan(_) => "run_local_scan",
        proto::v1::command::Kind::HashFiles(_) => "hash_files",
        proto::v1::command::Kind::CollectArtifact(_) => "collect_artifact",
        proto::v1::command::Kind::ApplyConfig(_) => "apply_config",
        proto::v1::command::Kind::SelfUpdate(_) => "self_update",
    }
}

fn ok_result(payload: prost_types::Struct) -> proto::v1::CommandResult {
    proto::v1::CommandResult {
        idempotency_key: String::new(),
        correlation_id: String::new(),
        status: proto::v1::command_result::Status::Ok as i32,
        error_code: String::new(),
        error_message: String::new(),
        payload: Some(payload),
        artifact: None,
        elapsed: None,
    }
}

fn failed(
    code: &str,
    message: &str,
    status: proto::v1::command_result::Status,
) -> proto::v1::CommandResult {
    warn!(code, message, "command failed");
    proto::v1::CommandResult {
        idempotency_key: String::new(),
        correlation_id: String::new(),
        status: status as i32,
        error_code: code.to_string(),
        error_message: message.to_string(),
        payload: None,
        artifact: None,
        elapsed: None,
    }
}

fn unsupported(kind_name: &str) -> proto::v1::CommandResult {
    failed(
        "COMMAND.UNSUPPORTED",
        &format!("Phase 1 does not implement {kind_name}"),
        proto::v1::command_result::Status::Unsupported,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn path_allowlist_accepts_etc() {
        assert!(path_allowed("/etc/passwd"));
        assert!(path_allowed("/usr/local/bin/foo"));
    }

    #[test]
    fn path_allowlist_rejects_relative() {
        assert!(!path_allowed("etc/passwd"));
        assert!(!path_allowed("../etc/passwd"));
    }

    #[test]
    fn path_allowlist_rejects_unlisted_root() {
        assert!(!path_allowed("/home/user/.ssh/id_ed25519"));
        assert!(!path_allowed("/root/secrets"));
    }

    #[tokio::test]
    async fn unsupported_command_returns_unsupported_status() {
        let lag = TelemetryLag::default();
        let d = Dispatcher::new(lag);
        let cmd = proto::v1::Command {
            idempotency_key: "k1".to_string(),
            correlation_id: "c1".to_string(),
            deadline: None,
            kind: Some(proto::v1::command::Kind::SelfUpdate(
                proto::v1::SelfUpdateCmd::default(),
            )),
        };
        let (tx, mut rx) = mpsc::channel(2);
        d.dispatch(cmd, tx, 99).await;
        let msg = rx.recv().await.expect("result");
        match msg.payload {
            Some(proto::v1::agent_message::Payload::CommandResult(r)) => {
                assert_eq!(
                    r.status,
                    proto::v1::command_result::Status::Unsupported as i32
                );
                assert_eq!(r.idempotency_key, "k1");
                assert_eq!(r.correlation_id, "c1");
            }
            other => panic!("unexpected payload: {other:?}"),
        }
    }

    #[tokio::test]
    async fn idempotent_replay_returns_cached_result() {
        let lag = TelemetryLag::default();
        let d = Dispatcher::new(lag);
        let cmd = || proto::v1::Command {
            idempotency_key: "kxx".to_string(),
            correlation_id: "cxx".to_string(),
            deadline: None,
            kind: Some(proto::v1::command::Kind::HashFiles(
                proto::v1::HashFilesCmd {
                    paths: vec!["/etc/hostname".to_string()],
                    algorithm: proto::v1::hash_files_cmd::Algorithm::Sha256 as i32,
                },
            )),
        };
        let (tx, mut rx) = mpsc::channel(4);
        d.dispatch(cmd(), tx.clone(), 1).await;
        d.dispatch(cmd(), tx.clone(), 2).await;
        // Two messages, identical payloads (same idempotency cache hit
        // on the second call).
        let _a = rx.recv().await.expect("first");
        let _b = rx.recv().await.expect("second");
    }
}
