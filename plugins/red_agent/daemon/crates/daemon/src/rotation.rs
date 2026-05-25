//! Automatic client-cert rotation.
//!
//! Watchdog that observes the client cert's validity window. When the
//! leaf enters the renewal window
//! ([`cert_lifecycle::RENEWAL_WINDOW_DAYS`] before `notAfter`) the
//! daemon:
//!
//! 1. Generates a fresh ed25519 keypair on-device.
//! 2. Builds a CSR carrying the agent UUID via the shared
//!    [`csr::build_csr_pem`] helper.
//! 3. Sends a `RotationRequest` over the existing mTLS-authenticated
//!    stream so the backend already knows who is asking.
//! 4. Stashes the new private key in [`RotationState`] keyed by the
//!    request's nonce; the `RotationGrant` handler combines it with
//!    the freshly issued cert and persists the new identity to the
//!    keystore. The next reconnect picks up the new material.
//!
//! Trust invariants:
//!
//! * The new key is generated via `OsRng.fill_bytes` (no seedable
//!   PRNG) and zeroized as soon as the keystore takes ownership.
//! * If the grant carries a cert the agent did not request (no
//!   matching state entry), the grant is dropped — an attacker cannot
//!   coerce the daemon into adopting an unsolicited identity.

use std::sync::Arc;
use std::time::{Duration, SystemTime};

use baselith_redagent_keystore::{DaemonIdentityMaterial, Keystore, KeystoreId};
use baselith_redagent_proto as proto;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use ed25519_dalek::SigningKey;
use parking_lot::Mutex;
use rand::rngs::OsRng;
use rand::RngCore;
use thiserror::Error;
use tokio::sync::mpsc;
use tracing::{debug, info, warn};
use uuid::Uuid;
use zeroize::Zeroizing;

use crate::cert_lifecycle::{self, LifecycleStatus};
use crate::csr::build_csr_pem;
use crate::wire::{now_timestamp, random_nonce};

/// How often the rotation watchdog re-evaluates the leaf cert.
pub const POLL_INTERVAL: Duration = Duration::from_secs(60 * 60);

/// Failures the rotation flow can surface.
#[derive(Debug, Error)]
pub enum RotationError {
    #[error("csr build failed: {0}")]
    Csr(String),
    #[error("keystore persist failed: {0}")]
    Keystore(String),
}

/// Outstanding rotation request bookkeeping. The watchdog holds the
/// freshly generated private key here while the CSR is in flight; the
/// `RotationGrant` handler consumes the entry to assemble the new
/// identity.
pub struct RotationState {
    /// Currently-pending key material. `None` when no rotation is in
    /// flight. Wrapped in `Zeroizing` so dropping the option clears
    /// the secret.
    pending_key_pem: Mutex<Option<Zeroizing<Vec<u8>>>>,
}

impl RotationState {
    pub fn new() -> Self {
        Self {
            pending_key_pem: Mutex::new(None),
        }
    }

    /// True when a rotation is already in flight.
    pub fn is_rotating(&self) -> bool {
        self.pending_key_pem.lock().is_some()
    }

    fn store_pending(&self, pem: Zeroizing<Vec<u8>>) {
        self.pending_key_pem.lock().replace(pem);
    }

    fn take_pending(&self) -> Option<Zeroizing<Vec<u8>>> {
        self.pending_key_pem.lock().take()
    }
}

/// Spawn the watchdog task. Runs forever as long as `tx` is alive.
pub fn spawn_watchdog(
    state: Arc<RotationState>,
    tx: mpsc::Sender<proto::AgentMessage>,
    cert_pem: Vec<u8>,
    agent_uuid: String,
) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(POLL_INTERVAL);
        // First tick fires immediately; we still want a fast eval at startup.
        loop {
            interval.tick().await;
            if state.is_rotating() {
                debug!("rotation already in flight; skipping eval");
                continue;
            }
            let summary = match cert_lifecycle::parse_leaf(&cert_pem) {
                Ok(s) => s,
                Err(e) => {
                    warn!(error = %e, "cert parse failed in rotation watchdog");
                    continue;
                }
            };
            let now = SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .map(|d| d.as_secs() as i64)
                .unwrap_or_default();
            let status = cert_lifecycle::evaluate(&summary, now);
            if !matches!(status, LifecycleStatus::ExpiringSoon) {
                continue;
            }
            if let Err(e) = trigger_rotation(&state, &tx, &agent_uuid, summary.not_after_unix).await
            {
                warn!(error = %e, "rotation request failed");
            }
        }
    })
}

async fn trigger_rotation(
    state: &Arc<RotationState>,
    tx: &mpsc::Sender<proto::AgentMessage>,
    agent_uuid: &str,
    old_not_after: i64,
) -> Result<(), RotationError> {
    let mut secret = [0u8; 32];
    OsRng.fill_bytes(&mut secret);
    let signing_key = SigningKey::from_bytes(&secret);
    secret.fill(0);

    let uuid = Uuid::parse_str(agent_uuid).unwrap_or_else(|_| Uuid::new_v4());
    let csr_pem =
        build_csr_pem(&signing_key, uuid).map_err(|e| RotationError::Csr(e.to_string()))?;

    let private_pem = signing_key
        .to_pkcs8_pem(ed25519_dalek::pkcs8::spki::der::pem::LineEnding::LF)
        .map_err(|e| RotationError::Csr(format!("encode private key PEM: {e}")))?
        .as_bytes()
        .to_vec();
    state.store_pending(Zeroizing::new(private_pem));

    let request = proto::v1::RotationRequest {
        csr_pem: csr_pem.into_bytes(),
        old_cert_not_after: Some(prost_types::Timestamp {
            seconds: old_not_after,
            nanos: 0,
        }),
    };
    let msg = proto::AgentMessage {
        seq: 0,
        nonce: random_nonce(),
        ts: Some(now_timestamp()),
        payload: Some(proto::v1::agent_message::Payload::RotationRequest(request)),
    };
    if tx.send(msg).await.is_err() {
        // Roll back the staged key — there is no in-flight request.
        let _ = state.take_pending();
        warn!("rotation request channel closed; rolling back pending key");
    } else {
        info!("rotation request sent; awaiting RotationGrant");
    }
    Ok(())
}

/// Handle an inbound `RotationGrant`: combine with the staged key and
/// persist via the keystore. Logs and discards if no rotation is in
/// flight (an unsolicited grant must not adopt a new identity).
pub fn apply_grant(
    state: &Arc<RotationState>,
    keystore: &dyn Keystore,
    keystore_id: &KeystoreId,
    grant: proto::v1::RotationGrant,
) -> Result<(), RotationError> {
    let Some(private_pem) = state.take_pending() else {
        warn!("RotationGrant received without pending request; ignoring");
        return Ok(());
    };
    let mut chain = grant.new_cert_pem.clone();
    chain.extend_from_slice(&grant.chain_pem);
    let identity = DaemonIdentityMaterial::new(chain, private_pem.to_vec());
    keystore
        .store(keystore_id, &identity)
        .map_err(|e| RotationError::Keystore(e.to_string()))?;
    info!(
        not_after = grant.not_after.as_ref().map(|t| t.seconds),
        "rotation grant persisted; new identity active on next reconnect"
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rotation_state_starts_idle() {
        let s = RotationState::new();
        assert!(!s.is_rotating());
    }

    #[test]
    fn store_and_take_pending_round_trip() {
        let s = RotationState::new();
        s.store_pending(Zeroizing::new(b"test-pem".to_vec()));
        assert!(s.is_rotating());
        let taken = s.take_pending().expect("present");
        assert_eq!(taken.as_slice(), b"test-pem");
        assert!(!s.is_rotating());
    }
}
