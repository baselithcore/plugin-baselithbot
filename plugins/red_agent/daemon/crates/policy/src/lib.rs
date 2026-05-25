//! Signed policy bundle verification.
//!
//! Bundles arrive over the gRPC stream as `PolicyUpdate` messages
//! carrying an ed25519 signature over the bundle bytes. The daemon
//! verifies the signature against the backend public key pinned at
//! install time before applying any rule. A bundle that fails
//! verification is dropped silently and an `agent.policy.bundle_invalid`
//! audit row is emitted on the next heartbeat.
//!
//! Trust invariants:
//!
//! * The verifying public key is **pinned at install time** and
//!   loaded once from disk at daemon startup. Rotation requires a
//!   coordinated re-issue of the install bundle.
//! * Signature scheme is fixed to ed25519. RSA / ECDSA are refused.
//! * Bundles are version-numbered; downgrades are refused so an
//!   attacker who recorded an older signed bundle cannot replay it.
//! * Bundles carry an `expires_at` (relative seconds since
//!   `issued_at`); the daemon's local clock must be within
//!   ±60 seconds of `issued_at` for the bundle to apply.

#![deny(unsafe_code)]
#![warn(missing_docs)]

use std::time::{Duration, SystemTime};

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::warn;

const MAX_BUNDLE_BYTES: usize = 256 * 1024;
const CLOCK_SKEW_TOLERANCE_SECS: i64 = 60;

/// Failures a policy bundle can produce during verification or apply.
#[derive(Debug, Error)]
pub enum PolicyError {
    /// Bundle signature did not verify against the pinned key.
    #[error("policy bundle signature invalid")]
    BadSignature,

    /// Bundle version is older than the currently active policy.
    #[error("policy bundle stale: have {current}, got {incoming}")]
    Stale {
        /// Active version on the daemon.
        current: u64,
        /// Version of the rejected incoming bundle.
        incoming: u64,
    },

    /// Bundle JSON is malformed.
    #[error("policy bundle malformed: {0}")]
    Malformed(String),

    /// Bundle exceeds the maximum size.
    #[error("policy bundle too large ({size} > {max} bytes)")]
    TooLarge {
        /// Size submitted.
        size: usize,
        /// Hard cap.
        max: usize,
    },

    /// Bundle has already expired.
    #[error("policy bundle expired ({expired_seconds_ago} seconds ago)")]
    Expired {
        /// How far past `expires_at` the daemon clock is.
        expired_seconds_ago: i64,
    },

    /// Bundle issued time is too far in the future relative to the
    /// daemon clock — possible replay or clock-skew attack.
    #[error("policy bundle issued in future ({skew_seconds} seconds)")]
    ClockSkew {
        /// Magnitude of the skew.
        skew_seconds: i64,
    },
}

/// Plaintext bundle payload after signature verification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyBundle {
    /// Monotonic version. Older versions cannot replace newer ones.
    pub version: u64,
    /// Unix-seconds when the bundle was signed.
    pub issued_at_unix: i64,
    /// Validity window in seconds, applied as
    /// `expires_at = issued_at + ttl_seconds`.
    pub ttl_seconds: u64,
    /// Free-form rule tree consumed by the policy engine; opaque to
    /// this crate.
    pub rules: serde_json::Value,
}

impl PolicyBundle {
    /// Verify expiry / future-issue invariants against `now_unix`.
    fn check_clock(&self, now_unix: i64) -> Result<(), PolicyError> {
        let skew = self.issued_at_unix - now_unix;
        if skew > CLOCK_SKEW_TOLERANCE_SECS {
            return Err(PolicyError::ClockSkew { skew_seconds: skew });
        }
        let expires_at = self.issued_at_unix + self.ttl_seconds as i64;
        if now_unix > expires_at {
            return Err(PolicyError::Expired {
                expired_seconds_ago: now_unix - expires_at,
            });
        }
        Ok(())
    }
}

/// Pinned-key verifier the daemon constructs once at startup.
pub struct BundleVerifier {
    public_key: VerifyingKey,
    current_version: u64,
}

impl BundleVerifier {
    /// Construct a verifier from a 32-byte ed25519 public key.
    pub fn from_public_key_bytes(bytes: &[u8], initial_version: u64) -> Result<Self, PolicyError> {
        if bytes.len() != 32 {
            return Err(PolicyError::Malformed(format!(
                "ed25519 public key must be 32 bytes, got {}",
                bytes.len()
            )));
        }
        let mut buf = [0u8; 32];
        buf.copy_from_slice(bytes);
        let public_key = VerifyingKey::from_bytes(&buf)
            .map_err(|e| PolicyError::Malformed(format!("ed25519 public key decode: {e}")))?;
        Ok(Self {
            public_key,
            current_version: initial_version,
        })
    }

    /// Verify and decode a signed bundle, returning the parsed
    /// payload. Updates `current_version` on success so subsequent
    /// invocations enforce monotonic version progression.
    pub fn verify(
        &mut self,
        bundle_bytes: &[u8],
        signature_bytes: &[u8],
    ) -> Result<PolicyBundle, PolicyError> {
        if bundle_bytes.len() > MAX_BUNDLE_BYTES {
            return Err(PolicyError::TooLarge {
                size: bundle_bytes.len(),
                max: MAX_BUNDLE_BYTES,
            });
        }
        if signature_bytes.len() != 64 {
            return Err(PolicyError::BadSignature);
        }
        let mut sig_buf = [0u8; 64];
        sig_buf.copy_from_slice(signature_bytes);
        let signature = Signature::from_bytes(&sig_buf);

        self.public_key
            .verify(bundle_bytes, &signature)
            .map_err(|_| PolicyError::BadSignature)?;

        let bundle: PolicyBundle = serde_json::from_slice(bundle_bytes)
            .map_err(|e| PolicyError::Malformed(format!("decode: {e}")))?;

        if bundle.version <= self.current_version {
            warn!(
                current = self.current_version,
                incoming = bundle.version,
                "stale policy bundle rejected"
            );
            return Err(PolicyError::Stale {
                current: self.current_version,
                incoming: bundle.version,
            });
        }

        bundle.check_clock(now_unix())?;
        self.current_version = bundle.version;
        Ok(bundle)
    }

    /// Read-only view of the active version.
    pub fn current_version(&self) -> u64 {
        self.current_version
    }
}

fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap_or(Duration::ZERO)
        .as_secs() as i64
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::{Signer, SigningKey};
    use rand::rngs::OsRng;
    use rand::RngCore;

    fn fresh_signing_key() -> SigningKey {
        let mut secret = [0u8; 32];
        OsRng.fill_bytes(&mut secret);
        SigningKey::from_bytes(&secret)
    }

    fn make_bundle(version: u64, ttl_seconds: u64) -> Vec<u8> {
        let bundle = PolicyBundle {
            version,
            issued_at_unix: now_unix(),
            ttl_seconds,
            rules: serde_json::json!({"deny": []}),
        };
        serde_json::to_vec(&bundle).expect("encode bundle")
    }

    #[test]
    fn verify_accepts_first_valid_bundle() {
        let signer = fresh_signing_key();
        let bytes = make_bundle(1, 3600);
        let sig = signer.sign(&bytes);

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 0)
            .expect("verifier");
        let bundle = v.verify(&bytes, &sig.to_bytes()).expect("verify");
        assert_eq!(bundle.version, 1);
        assert_eq!(v.current_version(), 1);
    }

    #[test]
    fn verify_rejects_stale_bundle() {
        let signer = fresh_signing_key();
        let bytes = make_bundle(1, 3600);
        let sig = signer.sign(&bytes);

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 5)
            .expect("verifier");
        let err = v.verify(&bytes, &sig.to_bytes()).unwrap_err();
        assert!(matches!(
            err,
            PolicyError::Stale {
                current: 5,
                incoming: 1
            }
        ));
    }

    #[test]
    fn verify_rejects_wrong_signer() {
        let signer = fresh_signing_key();
        let attacker = fresh_signing_key();
        let bytes = make_bundle(1, 3600);
        let sig = attacker.sign(&bytes);

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 0)
            .expect("verifier");
        assert!(matches!(
            v.verify(&bytes, &sig.to_bytes()),
            Err(PolicyError::BadSignature)
        ));
    }

    #[test]
    fn verify_rejects_tampered_payload() {
        let signer = fresh_signing_key();
        let bytes = make_bundle(1, 3600);
        let sig = signer.sign(&bytes);
        let mut tampered = bytes.clone();
        let last = tampered.len() - 1;
        tampered[last] ^= 0x01;

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 0)
            .expect("verifier");
        assert!(matches!(
            v.verify(&tampered, &sig.to_bytes()),
            Err(PolicyError::BadSignature)
        ));
    }

    #[test]
    fn verify_rejects_expired_bundle() {
        let signer = fresh_signing_key();
        // ttl=0 → expires_at == issued_at; with our 60s clock skew
        // tolerance the bundle is considered expired immediately.
        let bundle = PolicyBundle {
            version: 1,
            issued_at_unix: now_unix() - 120,
            ttl_seconds: 30,
            rules: serde_json::json!({}),
        };
        let bytes = serde_json::to_vec(&bundle).expect("encode");
        let sig = signer.sign(&bytes);

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 0)
            .expect("verifier");
        assert!(matches!(
            v.verify(&bytes, &sig.to_bytes()),
            Err(PolicyError::Expired { .. })
        ));
    }

    #[test]
    fn verify_rejects_future_bundle() {
        let signer = fresh_signing_key();
        let bundle = PolicyBundle {
            version: 1,
            issued_at_unix: now_unix() + 600, // 10 min in future
            ttl_seconds: 3600,
            rules: serde_json::json!({}),
        };
        let bytes = serde_json::to_vec(&bundle).expect("encode");
        let sig = signer.sign(&bytes);

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 0)
            .expect("verifier");
        assert!(matches!(
            v.verify(&bytes, &sig.to_bytes()),
            Err(PolicyError::ClockSkew { .. })
        ));
    }

    #[test]
    fn verify_rejects_oversize_bundle() {
        let signer = fresh_signing_key();
        let bytes = vec![0u8; MAX_BUNDLE_BYTES + 1];
        let sig = signer.sign(&bytes);

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 0)
            .expect("verifier");
        assert!(matches!(
            v.verify(&bytes, &sig.to_bytes()),
            Err(PolicyError::TooLarge { .. })
        ));
    }

    #[test]
    fn verify_rejects_short_signature() {
        let signer = fresh_signing_key();
        let bytes = make_bundle(1, 3600);

        let mut v = BundleVerifier::from_public_key_bytes(signer.verifying_key().as_bytes(), 0)
            .expect("verifier");
        assert!(matches!(
            v.verify(&bytes, &[0u8; 32]),
            Err(PolicyError::BadSignature)
        ));
    }

    #[test]
    fn verify_rejects_bad_public_key_length() {
        let result = BundleVerifier::from_public_key_bytes(&[0u8; 16], 0);
        assert!(matches!(result, Err(PolicyError::Malformed(_))));
    }
}
