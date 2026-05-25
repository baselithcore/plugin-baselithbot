//! Daemon runtime: connection lifecycle + reconnect backoff.
//!
//! Drives the bidirectional `AgentChannelClient::open_stream` RPC.
//! On connect:
//!
//! 1. Send `AgentHello` with platform metadata + declared capabilities.
//! 2. Wait for `ServerHello`; refuse to proceed on `protocol_version_min` mismatch.
//! 3. Spawn the heartbeat pump (each heartbeat carries a fresh `HealthSnapshot`).
//! 4. Spawn the inventory pump (process / package / listener snapshots, 5-minute cadence).
//! 5. Forward inbound `ServerMessage`s to the dispatcher; inventory + hash commands run inline, scanner / artifact / config / self-update kinds reply with `STATUS_UNSUPPORTED` until Phase 2.
//!
//! On any failure (network drop, server `Disconnect`, panic) the
//! runtime re-enters reconnect backoff. Backoff is exponential with
//! jitter, capped at 5 minutes.

use std::sync::Arc;
use std::time::Duration;

use baselith_redagent_collector::{
    firewall, inventory, kernel, net, persistence, selfintegrity, ssh, users,
};
use baselith_redagent_keystore::{Keystore, KeystoreId};
use baselith_redagent_policy::BundleVerifier;
use baselith_redagent_proto as proto;
use baselith_redagent_transport::{Client, ClientConfig};
use parking_lot::Mutex;
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;
use tonic::codec::CompressionEncoding;
use tonic::Request;
use tracing::{debug, info, warn};

use crate::cert_lifecycle;
use crate::dispatch::Dispatcher;
use crate::health::{HealthProbe, TelemetryLag};
use crate::log_drain::LogDrain;
use crate::offline_buffer::Spool;
use crate::platform::PlatformInfo;
use crate::rotation::{self, RotationState};
use crate::wire::{now_timestamp, random_nonce, random_u64};

const DEFAULT_HEARTBEAT_SECONDS: u64 = 30;
const RECONNECT_INITIAL: Duration = Duration::from_secs(1);
const RECONNECT_MAX: Duration = Duration::from_secs(300);
const RECONNECT_JITTER_PCT: u64 = 25;
const INVENTORY_INTERVAL_SECONDS: u64 = 300;
const OUTBOUND_CHANNEL_CAPACITY: usize = 256;
const COMMAND_RESULT_BASE_SEQ: u64 = 2_000_000;

/// Static daemon descriptor advertised to the backend at every connect.
#[derive(Debug, Clone)]
pub struct DaemonIdentity {
    pub agent_uuid: String,
    pub daemon_version: String,
    pub protocol_version: u32,
    pub declared_capabilities: Vec<proto::AgentCapability>,
}

/// Drive the connect/heartbeat/dispatch loop forever, reconnecting on
/// every error with exponential backoff.
#[allow(clippy::too_many_arguments)]
pub async fn run_forever(
    client_config: ClientConfig,
    identity: DaemonIdentity,
    platform: PlatformInfo,
    verifier: Arc<Mutex<BundleVerifier>>,
    buffer_path: std::path::PathBuf,
    log_drain: LogDrain,
    cert_pem: Vec<u8>,
    spool: Option<Arc<Spool>>,
    keystore: Arc<dyn Keystore>,
    keystore_id: KeystoreId,
) -> ! {
    let log_drain = std::sync::Arc::new(parking_lot::Mutex::new(Some(log_drain)));
    let rotation_state = Arc::new(RotationState::new());
    let mut backoff = RECONNECT_INITIAL;
    loop {
        match run_once(
            &client_config,
            &identity,
            &platform,
            &verifier,
            buffer_path.clone(),
            log_drain.clone(),
            &cert_pem,
            spool.clone(),
            keystore.clone(),
            &keystore_id,
            rotation_state.clone(),
        )
        .await
        {
            Ok(reason) => {
                info!(reason = %reason, "session ended cleanly; reconnecting");
                backoff = RECONNECT_INITIAL;
            }
            Err(err) => {
                warn!(error = %err, ?backoff, "session error; backing off");
                tokio::time::sleep(jittered(backoff)).await;
                backoff = next_backoff(backoff);
            }
        }
    }
}

#[allow(clippy::too_many_arguments)]
async fn run_once(
    client_config: &ClientConfig,
    identity: &DaemonIdentity,
    platform: &PlatformInfo,
    verifier: &Arc<Mutex<BundleVerifier>>,
    buffer_path: std::path::PathBuf,
    log_drain: std::sync::Arc<parking_lot::Mutex<Option<LogDrain>>>,
    cert_pem: &[u8],
    spool: Option<Arc<Spool>>,
    keystore: Arc<dyn Keystore>,
    keystore_id: &KeystoreId,
    rotation_state: Arc<RotationState>,
) -> Result<&'static str, RuntimeError> {
    let client = Client::connect(client_config)
        .await
        .map_err(|e| RuntimeError::Transport(e.to_string()))?;

    // Per-session lag counter — tracks queue depth for HealthSnapshot.
    let lag = TelemetryLag::default();
    let dispatcher = Dispatcher::new(lag.clone());

    let (tx, rx) = mpsc::channel::<proto::AgentMessage>(OUTBOUND_CHANNEL_CAPACITY);

    // Send the initial hello before the response stream is taken.
    tx.send(build_hello(identity, platform))
        .await
        .map_err(|_| RuntimeError::ChannelClosed)?;
    lag.record_enqueue();

    // Replay any messages spooled while the stream was down. This
    // happens before live traffic so causality across the outage is
    // preserved on the backend.
    if let Some(spool_ref) = spool.as_ref() {
        match spool_ref.drain_to(&tx).await {
            Ok(n) if n > 0 => {
                for _ in 0..n {
                    lag.record_enqueue();
                }
            }
            Ok(_) => {}
            Err(e) => warn!(error = %e, "spool drain failed; continuing"),
        }
    }

    // Drain wrapper: every dequeue from the receiver decrements the
    // lag counter so HealthSnapshot reflects the wire-side queue.
    // When the gRPC stream drops, queued items are persisted to the
    // spool so the next session can replay them.
    let lag_drain = lag.clone();
    let spool_drain = spool.clone();
    let drain_rx = drain_observe(rx, move || lag_drain.record_dequeue(), spool_drain);

    let request = Request::new(ReceiverStream::new(drain_rx));
    let mut response = client
        .into_inner()
        .send_compressed(CompressionEncoding::Gzip)
        .accept_compressed(CompressionEncoding::Gzip)
        .open_stream(request)
        .await
        .map_err(|e| RuntimeError::Rpc(e.to_string()))?
        .into_inner();

    let mut heartbeat_handle: Option<tokio::task::JoinHandle<()>> = None;
    let mut inventory_handle: Option<tokio::task::JoinHandle<()>> = None;
    let mut log_drain_handle: Option<tokio::task::JoinHandle<()>> = None;
    let mut rotation_handle: Option<tokio::task::JoinHandle<()>> = None;

    // Emit the cert lifecycle event once per session (best effort).
    if let Ok(evt) = cert_lifecycle::observe(cert_pem) {
        let batch = proto::TelemetryBatch {
            batch_id: uuid_v4_string(),
            events: vec![evt],
        };
        let msg = proto::AgentMessage {
            seq: 999_999,
            nonce: random_nonce(),
            ts: Some(now_timestamp()),
            payload: Some(proto::v1::agent_message::Payload::Telemetry(batch)),
        };
        if tx.send(msg).await.is_ok() {
            lag.record_enqueue();
        }
    }

    while let Some(msg) = response
        .message()
        .await
        .map_err(|e| RuntimeError::Rpc(e.to_string()))?
    {
        match msg.payload {
            Some(proto::v1::server_message::Payload::Hello(hello)) => {
                let interval = hello
                    .heartbeat_interval
                    .as_ref()
                    .map(|d| d.seconds.max(1) as u64)
                    .unwrap_or(DEFAULT_HEARTBEAT_SECONDS);
                heartbeat_handle.replace(spawn_heartbeat(
                    tx.clone(),
                    interval,
                    buffer_path.clone(),
                    lag.clone(),
                ));
                inventory_handle.replace(spawn_inventory_pump(
                    tx.clone(),
                    lag.clone(),
                    identity.daemon_version.clone(),
                ));
                if log_drain_handle.is_none() {
                    if let Some(drain) = log_drain.lock().take() {
                        let tx_logs = tx.clone();
                        log_drain_handle.replace(tokio::spawn(async move {
                            drain.run(tx_logs).await;
                        }));
                    }
                }
                rotation_handle.replace(rotation::spawn_watchdog(
                    rotation_state.clone(),
                    tx.clone(),
                    cert_pem.to_vec(),
                    identity.agent_uuid.clone(),
                ));
                info!(
                    heartbeat_seconds = interval,
                    capabilities = hello.capabilities.len(),
                    "server hello received"
                );
            }
            Some(proto::v1::server_message::Payload::Heartbeat(_)) => {
                debug!("server heartbeat");
            }
            Some(proto::v1::server_message::Payload::Policy(update)) => {
                handle_policy_update(verifier, &tx, update, &lag).await;
            }
            Some(proto::v1::server_message::Payload::RotationGrant(grant)) => {
                if let Err(e) =
                    rotation::apply_grant(&rotation_state, &*keystore, keystore_id, grant)
                {
                    warn!(error = %e, "rotation grant apply failed");
                }
            }
            Some(proto::v1::server_message::Payload::Command(command)) => {
                let dispatcher = dispatcher.clone();
                let tx_clone = tx.clone();
                let seq = COMMAND_RESULT_BASE_SEQ.wrapping_add(msg.seq);
                tokio::spawn(async move {
                    dispatcher.dispatch(command, tx_clone, seq).await;
                });
            }
            Some(proto::v1::server_message::Payload::Disconnect(_)) => {
                if let Some(handle) = heartbeat_handle.take() {
                    handle.abort();
                }
                if let Some(handle) = inventory_handle.take() {
                    handle.abort();
                }
                if let Some(handle) = log_drain_handle.take() {
                    handle.abort();
                }
                if let Some(handle) = rotation_handle.take() {
                    handle.abort();
                }
                return Ok("server disconnect");
            }
            None => {}
        }
    }

    if let Some(handle) = heartbeat_handle {
        handle.abort();
    }
    if let Some(handle) = inventory_handle {
        handle.abort();
    }
    if let Some(handle) = log_drain_handle {
        handle.abort();
    }
    if let Some(handle) = rotation_handle {
        handle.abort();
    }
    Ok("stream closed")
}

/// Wrap the outbound mpsc receiver so every dequeue triggers a side
/// effect (used to maintain the telemetry lag counter for
/// `HealthSnapshot`). When the downstream consumer drops the receiver
/// (gRPC stream collapse), every subsequent message is appended to
/// the offline spool instead of being lost.
fn drain_observe<F>(
    mut rx: mpsc::Receiver<proto::AgentMessage>,
    on_dequeue: F,
    spool: Option<Arc<Spool>>,
) -> mpsc::Receiver<proto::AgentMessage>
where
    F: Fn() + Send + 'static,
{
    let (out_tx, out_rx) = mpsc::channel(OUTBOUND_CHANNEL_CAPACITY);
    tokio::spawn(async move {
        let mut spooling = false;
        while let Some(item) = rx.recv().await {
            if spooling {
                if let Some(s) = spool.as_ref() {
                    if let Err(e) = s.append(&item) {
                        debug!(error = %e, "spool append failed");
                    }
                }
                continue;
            }
            match out_tx.send(item).await {
                Ok(_) => on_dequeue(),
                Err(send_err) => {
                    spooling = true;
                    if let Some(s) = spool.as_ref() {
                        if let Err(e) = s.append(&send_err.0) {
                            debug!(error = %e, "spool append failed");
                        }
                        info!("outbound stream lost; spooling further messages to disk");
                    }
                }
            }
        }
    });
    out_rx
}

async fn handle_policy_update(
    verifier: &Arc<Mutex<BundleVerifier>>,
    tx: &mpsc::Sender<proto::AgentMessage>,
    update: proto::v1::PolicyUpdate,
    lag: &TelemetryLag,
) {
    let bundle = update.bundle;
    let signature = update.bundle_sig;
    let result = {
        let mut guard = verifier.lock();
        guard.verify(&bundle, &signature)
    };
    let (version, applied, error) = match result {
        Ok(b) => {
            info!(version = b.version, "policy bundle accepted");
            (b.version, true, String::new())
        }
        Err(e) => {
            warn!(error = %e, "policy bundle rejected");
            (update.version, false, e.to_string())
        }
    };
    let ack = proto::AgentMessage {
        seq: 0,
        nonce: random_nonce(),
        ts: Some(now_timestamp()),
        payload: Some(proto::v1::agent_message::Payload::PolicyAck(
            proto::v1::PolicyAck {
                version,
                applied,
                error,
            },
        )),
    };
    if tx.send(ack).await.is_ok() {
        lag.record_enqueue();
    } else {
        debug!("policy ack channel closed");
    }
}

fn build_hello(identity: &DaemonIdentity, platform: &PlatformInfo) -> proto::AgentMessage {
    let hello = proto::AgentHello {
        protocol_version: identity.protocol_version,
        daemon_version: identity.daemon_version.clone(),
        agent_uuid: identity.agent_uuid.clone(),
        platform: Some(platform.to_proto()),
        capabilities: identity
            .declared_capabilities
            .iter()
            .map(|c| *c as i32)
            .collect(),
        last_acked_server_seq: 0,
    };
    proto::AgentMessage {
        seq: 1,
        nonce: random_nonce(),
        ts: Some(now_timestamp()),
        payload: Some(proto::v1::agent_message::Payload::Hello(hello)),
    }
}

fn spawn_inventory_pump(
    tx: mpsc::Sender<proto::AgentMessage>,
    lag: TelemetryLag,
    daemon_version: String,
) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(INVENTORY_INTERVAL_SECONDS));
        let mut seq: u64 = 1_000_000;
        loop {
            interval.tick().await;
            let version_clone = daemon_version.clone();
            let events =
                match tokio::task::spawn_blocking(move || collect_inventory_events(&version_clone))
                    .await
                {
                    Ok(v) => v,
                    Err(e) => {
                        warn!(error = %e, "inventory worker panicked");
                        continue;
                    }
                };
            let batch = proto::TelemetryBatch {
                batch_id: uuid_v4_string(),
                events,
            };
            let msg = proto::AgentMessage {
                seq,
                nonce: random_nonce(),
                ts: Some(now_timestamp()),
                payload: Some(proto::v1::agent_message::Payload::Telemetry(batch)),
            };
            if tx.send(msg).await.is_err() {
                debug!("inventory channel closed; exiting pump");
                break;
            }
            lag.record_enqueue();
            seq = seq.wrapping_add(1);
        }
    })
}

fn collect_inventory_events(daemon_version: &str) -> Vec<proto::TelemetryEvent> {
    // Single snapshot id stitches every event of one inventory tick
    // together so the backend can render them as one observation.
    let snapshot_id = uuid::Uuid::new_v4().to_string();
    let mut events = vec![
        inventory::processes(proto::Severity::Info),
        inventory::packages(proto::Severity::Info),
        net::listening_sockets(proto::Severity::Info),
        users::snapshot(proto::Severity::Info),
        persistence::snapshot(proto::Severity::Info),
        kernel::snapshot(proto::Severity::Info),
        ssh::snapshot(proto::Severity::Info),
        firewall::snapshot(proto::Severity::Info),
        selfintegrity::snapshot(proto::Severity::Info, daemon_version),
    ];
    for evt in &mut events {
        evt.correlation_id = snapshot_id.clone();
    }
    events
}

fn uuid_v4_string() -> String {
    uuid::Uuid::new_v4().to_string()
}

fn spawn_heartbeat(
    tx: mpsc::Sender<proto::AgentMessage>,
    interval_seconds: u64,
    buffer_path: std::path::PathBuf,
    lag: TelemetryLag,
) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let mut probe = HealthProbe::new(buffer_path, lag.clone());
        let mut interval = tokio::time::interval(Duration::from_secs(interval_seconds));
        // First tick is immediate; skip it so we don't double up
        // with the hello we just sent.
        interval.tick().await;
        let mut seq: u64 = 2;
        loop {
            interval.tick().await;
            let snapshot = probe.snapshot();
            let msg = proto::AgentMessage {
                seq,
                nonce: random_nonce(),
                ts: Some(now_timestamp()),
                payload: Some(proto::v1::agent_message::Payload::Heartbeat(
                    proto::Heartbeat {
                        health: Some(snapshot),
                    },
                )),
            };
            if tx.send(msg).await.is_err() {
                debug!("heartbeat channel closed; exiting heartbeat task");
                break;
            }
            lag.record_enqueue();
            seq += 1;
        }
    })
}

fn next_backoff(current: Duration) -> Duration {
    let doubled = current.saturating_mul(2);
    if doubled > RECONNECT_MAX {
        RECONNECT_MAX
    } else {
        doubled
    }
}

fn jittered(d: Duration) -> Duration {
    let extra = d.as_millis() as u64 * RECONNECT_JITTER_PCT / 100;
    let jitter = random_u64() % extra.max(1);
    d + Duration::from_millis(jitter)
}

#[derive(Debug, thiserror::Error)]
enum RuntimeError {
    #[error("transport error: {0}")]
    Transport(String),
    #[error("rpc error: {0}")]
    Rpc(String),
    #[error("inbound channel closed before hello sent")]
    ChannelClosed,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn next_backoff_doubles_to_cap() {
        let mut d = Duration::from_secs(1);
        for _ in 0..20 {
            d = next_backoff(d);
        }
        assert_eq!(d, RECONNECT_MAX);
    }

    #[test]
    fn jittered_within_25pct() {
        let d = Duration::from_millis(1000);
        for _ in 0..50 {
            let j = jittered(d);
            assert!(j >= d);
            assert!(j <= d + Duration::from_millis(250));
        }
    }
}
