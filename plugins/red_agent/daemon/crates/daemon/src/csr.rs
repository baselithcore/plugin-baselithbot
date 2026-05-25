//! Ed25519 CSR builder shared by enrollment and cert rotation.
//!
//! Both flows generate a fresh keypair on-device and submit a CSR to
//! the backend; the backend's CA signs it and returns the leaf cert
//! plus chain. The keypair never leaves the daemon process before
//! being handed to the keystore for at-rest encryption.
//!
//! Implementation notes:
//!
//! * `rcgen` is the only ASN.1 builder vendored in this crate; the
//!   runtime path never invokes it so the cost lives only in the
//!   enrollment / rotation paths.
//! * `rcgen` does not yet expose a way to import an `Ed25519PrivateKey`
//!   directly, so we round-trip through PKCS8.

use anyhow::{Context, Result};
use ed25519_dalek::pkcs8::EncodePrivateKey;
use ed25519_dalek::SigningKey;
use uuid::Uuid;

/// Build a PEM-encoded CSR for `signing_key` carrying the given
/// `agent_uuid` as common name and SAN. Returns the CSR PEM string.
pub fn build_csr_pem(signing_key: &SigningKey, agent_uuid: Uuid) -> Result<String> {
    use rcgen::{CertificateParams, KeyPair};

    let pkcs8 = signing_key
        .to_pkcs8_der()
        .context("encode private key PKCS8")?;
    let kp = KeyPair::try_from(pkcs8.as_bytes()).context("rcgen keypair from pkcs8")?;
    let mut params =
        CertificateParams::new(vec![format!("agent:{}", agent_uuid)]).context("rcgen params")?;
    params
        .distinguished_name
        .push(rcgen::DnType::CommonName, agent_uuid.to_string());

    let csr = params.serialize_request(&kp).context("serialize CSR")?;
    csr.pem().context("encode CSR PEM")
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::OsRng;
    use rand::RngCore;

    #[test]
    fn build_csr_round_trips() {
        let mut secret = [0u8; 32];
        OsRng.fill_bytes(&mut secret);
        let signing_key = SigningKey::from_bytes(&secret);
        let pem = build_csr_pem(&signing_key, Uuid::new_v4()).expect("build");
        assert!(pem.contains("BEGIN CERTIFICATE REQUEST"));
        assert!(pem.contains("END CERTIFICATE REQUEST"));
    }
}
