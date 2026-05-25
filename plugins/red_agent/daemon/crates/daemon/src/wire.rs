//! Shared wire-protocol helpers.
//!
//! `random_nonce` returns 16 cryptographically random bytes from the
//! OS RNG. Nonces are protocol replay-protection seeds — the receiver
//! tracks them inside a sliding window and rejects duplicates — so
//! the property required is unpredictability, not just uniqueness.
//! The previous time+counter implementation produced predictable
//! values that an attacker who could observe the daemon clock could
//! pre-compute, weakening the replay window.

use prost_types::Timestamp;
use rand::rngs::OsRng;
use rand::RngCore;

/// 16-byte cryptographically random nonce. Used in every outbound
/// `AgentMessage.nonce` field.
pub fn random_nonce() -> Vec<u8> {
    let mut out = [0u8; 16];
    OsRng.fill_bytes(&mut out);
    out.to_vec()
}

/// Sample a u64 from the OS RNG. Used by the reconnect-jitter helper.
pub fn random_u64() -> u64 {
    OsRng.next_u64()
}

/// Current wall-clock as a protobuf `Timestamp`.
pub fn now_timestamp() -> Timestamp {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    Timestamp {
        seconds: now.as_secs() as i64,
        nanos: now.subsec_nanos() as i32,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn random_nonce_is_16_bytes_and_unique() {
        let mut seen: HashSet<Vec<u8>> = HashSet::new();
        for _ in 0..256 {
            let n = random_nonce();
            assert_eq!(n.len(), 16);
            assert!(seen.insert(n), "nonce collision indicates non-OS RNG");
        }
    }

    #[test]
    fn random_u64_is_not_constant() {
        let a = random_u64();
        let b = random_u64();
        // 1 in 2^64 — tolerable in tests.
        assert_ne!(a, b);
    }
}
