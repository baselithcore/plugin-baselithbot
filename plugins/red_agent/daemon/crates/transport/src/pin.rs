//! Root CA fingerprint pinning.
//!
//! The daemon is shipped with the SHA-256 fingerprint of its
//! enrollment-time root CA baked into config. At every TLS handshake
//! the daemon walks the server's presented chain and asserts that at
//! least one cert's SubjectPublicKeyInfo SHA-256 matches the pinned
//! value. Successful chain validation against the system trust store
//! is **not** sufficient — a rogue intermediate signed by a public CA
//! still fails the pin.
//!
//! The functions here are sync, allocation-light, and deterministic
//! so they can be exercised by ordinary unit tests; the actual
//! hooking into `rustls` lives in the higher-level `Client` builder
//! in the next milestone.

use sha2::{Digest, Sha256};
use thiserror::Error;
use x509_parser::prelude::*;

/// Errors `verify_chain_against_pin` can raise.
#[derive(Debug, Error)]
pub enum PinError {
    /// One of the DER blobs in the chain failed to parse.
    #[error("certificate parse failed at index {index}: {reason}")]
    ParseFailed {
        /// Position of the offending cert in the chain.
        index: usize,
        /// Underlying parser error message.
        reason: String,
    },

    /// The pin string was not 64 lowercase hex characters.
    #[error("invalid pin format (expected 64 lowercase hex chars)")]
    BadPinFormat,

    /// The chain did not contain a cert matching the pin.
    #[error("pinned fingerprint not present in chain")]
    PinMismatch,
}

/// Walk a presented cert chain and verify at least one entry's
/// SubjectPublicKeyInfo SHA-256 matches `expected_pin_hex`.
///
/// `chain` is a list of DER-encoded certificates ordered leaf-first
/// (the order rustls hands to a `ServerCertVerifier`).
pub fn verify_chain_against_pin(chain: &[&[u8]], expected_pin_hex: &str) -> Result<(), PinError> {
    if !is_valid_pin(expected_pin_hex) {
        return Err(PinError::BadPinFormat);
    }

    for (index, der) in chain.iter().enumerate() {
        let (_rest, cert) = parse_x509_certificate(der).map_err(|e| PinError::ParseFailed {
            index,
            reason: e.to_string(),
        })?;

        let spki_der = cert.public_key().raw;
        let mut hasher = Sha256::new();
        hasher.update(spki_der);
        let digest = hasher.finalize();
        let hex = hex::encode(digest);
        if hex == expected_pin_hex {
            return Ok(());
        }
    }
    Err(PinError::PinMismatch)
}

/// Compute the SubjectPublicKeyInfo SHA-256 fingerprint of a single
/// DER-encoded cert. Returned as lowercase hex (64 chars).
pub fn fingerprint_spki_sha256(cert_der: &[u8]) -> Result<String, PinError> {
    let (_rest, cert) = parse_x509_certificate(cert_der).map_err(|e| PinError::ParseFailed {
        index: 0,
        reason: e.to_string(),
    })?;
    let mut hasher = Sha256::new();
    hasher.update(cert.public_key().raw);
    Ok(hex::encode(hasher.finalize()))
}

fn is_valid_pin(pin: &str) -> bool {
    pin.len() == 64
        && pin
            .chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_uppercase())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rcgen::{CertificateParams, KeyPair};

    /// Build a self-signed cert and return (DER, SPKI fingerprint).
    fn make_cert() -> (Vec<u8>, String) {
        let key = KeyPair::generate().expect("keypair");
        let params = CertificateParams::new(vec!["test".into()]).expect("params");
        let cert = params.self_signed(&key).expect("self-sign");
        let der = cert.der().to_vec();
        let pin = fingerprint_spki_sha256(&der).expect("fingerprint");
        (der, pin)
    }

    #[test]
    fn pin_match_succeeds() {
        let (der, pin) = make_cert();
        assert!(verify_chain_against_pin(&[der.as_slice()], &pin).is_ok());
    }

    #[test]
    fn pin_mismatch_fails() {
        let (der, _good) = make_cert();
        let bogus = "0".repeat(64);
        assert!(matches!(
            verify_chain_against_pin(&[der.as_slice()], &bogus),
            Err(PinError::PinMismatch)
        ));
    }

    #[test]
    fn malformed_pin_rejected() {
        let (der, _) = make_cert();
        assert!(matches!(
            verify_chain_against_pin(&[der.as_slice()], "not hex"),
            Err(PinError::BadPinFormat)
        ));
        let upper_hex = "AB".repeat(32);
        assert!(matches!(
            verify_chain_against_pin(&[der.as_slice()], &upper_hex),
            Err(PinError::BadPinFormat)
        ));
    }

    #[test]
    fn malformed_cert_in_chain_reports_index() {
        let (der, pin) = make_cert();
        let bad: &[u8] = b"\x00\x01\x02";
        let chain: &[&[u8]] = &[bad, der.as_slice()];
        // First entry is malformed -> ParseFailed { index: 0 }
        let err = verify_chain_against_pin(chain, &pin).unwrap_err();
        assert!(matches!(err, PinError::ParseFailed { index: 0, .. }));
    }

    #[test]
    fn pin_match_in_intermediate_succeeds() {
        // Even when the leaf doesn't match, finding the pin further
        // along the chain (e.g. on the intermediate / root) is a
        // valid trust assertion.
        let (leaf_der, _leaf_pin) = make_cert();
        let (root_der, root_pin) = make_cert();
        let chain: &[&[u8]] = &[leaf_der.as_slice(), root_der.as_slice()];
        assert!(verify_chain_against_pin(chain, &root_pin).is_ok());
    }
}
