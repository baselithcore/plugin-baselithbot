//! rustls `ClientConfig` factory with pinned-root verification.
//!
//! Builds a `rustls::ClientConfig` configured for:
//!
//! * TLS 1.3 only (no fallback negotiation).
//! * Custom `ServerCertVerifier` that calls
//!   [`crate::pin::verify_chain_against_pin`] before any other check.
//! * mTLS client identity loaded from PEM bytes.
//! * ALPN advertising `h2` so tonic can negotiate gRPC.
//!
//! The pin verifier is the *only* trust anchor. Standard CA chain
//! validation is intentionally bypassed: a rogue intermediate signed
//! by a public CA must not pass.

use std::sync::Arc;
use std::time::SystemTime;

use rustls::client::danger::{HandshakeSignatureValid, ServerCertVerified, ServerCertVerifier};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, ServerName, UnixTime};
use rustls::{ClientConfig, DigitallySignedStruct, Error as RustlsError, SignatureScheme};

use crate::pin::verify_chain_against_pin;
use crate::{Identity, TransportError};

/// Build a TLS-1.3-only client config with a pinned-root verifier.
///
/// ALPN is intentionally left empty here — `hyper-rustls`
/// (`HttpsConnectorBuilder::enable_http2`) is responsible for
/// installing the `h2` ALPN value. Pre-setting it on the
/// `ClientConfig` causes hyper-rustls to panic with
/// "ALPN protocols should not be pre-defined".
pub fn build_client_config(
    pinned_root_ca_fingerprint_sha256: &str,
    identity: &Identity,
) -> Result<Arc<ClientConfig>, TransportError> {
    let leaf_chain = parse_cert_chain(&identity.cert_chain_pem)?;
    let private_key = parse_private_key(&identity.private_key_pem)?;

    let provider = rustls::crypto::ring::default_provider();
    let _ = provider.clone().install_default(); // OK if already installed

    let verifier: Arc<dyn ServerCertVerifier> = Arc::new(PinnedServerCertVerifier {
        expected_pin: pinned_root_ca_fingerprint_sha256.to_string(),
        provider: provider.clone(),
    });

    let config = ClientConfig::builder_with_protocol_versions(&[&rustls::version::TLS13])
        .dangerous()
        .with_custom_certificate_verifier(verifier)
        .with_client_auth_cert(leaf_chain, private_key)
        .map_err(|e| TransportError::BadIdentity(e.to_string()))?;

    Ok(Arc::new(config))
}

#[derive(Debug)]
struct PinnedServerCertVerifier {
    expected_pin: String,
    provider: rustls::crypto::CryptoProvider,
}

impl ServerCertVerifier for PinnedServerCertVerifier {
    fn verify_server_cert(
        &self,
        end_entity: &CertificateDer<'_>,
        intermediates: &[CertificateDer<'_>],
        _server_name: &ServerName<'_>,
        _ocsp: &[u8],
        _now: UnixTime,
    ) -> Result<ServerCertVerified, RustlsError> {
        let mut chain: Vec<&[u8]> = Vec::with_capacity(intermediates.len() + 1);
        chain.push(end_entity.as_ref());
        for inter in intermediates {
            chain.push(inter.as_ref());
        }
        verify_chain_against_pin(&chain, &self.expected_pin)
            .map_err(|e| RustlsError::General(format!("pinned-root verification failed: {e}")))?;
        Ok(ServerCertVerified::assertion())
    }

    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, RustlsError> {
        // TLS 1.3 only: refuse 1.2 signature paths so a downgrade
        // attempt fails closed instead of silently accepting.
        Err(RustlsError::General("TLS 1.2 not supported".into()))
    }

    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, RustlsError> {
        rustls::crypto::verify_tls13_signature(
            message,
            cert,
            dss,
            &self.provider.signature_verification_algorithms,
        )
    }

    fn supported_verify_schemes(&self) -> Vec<SignatureScheme> {
        self.provider
            .signature_verification_algorithms
            .supported_schemes()
    }
}

fn parse_cert_chain(pem: &[u8]) -> Result<Vec<CertificateDer<'static>>, TransportError> {
    let mut reader = std::io::BufReader::new(pem);
    let chain: Result<Vec<_>, _> = rustls_pemfile::certs(&mut reader).collect();
    let chain = chain.map_err(|e| TransportError::BadIdentity(format!("cert chain: {e}")))?;
    if chain.is_empty() {
        return Err(TransportError::BadIdentity(
            "no certificates in chain".to_string(),
        ));
    }
    Ok(chain)
}

fn parse_private_key(pem: &[u8]) -> Result<PrivateKeyDer<'static>, TransportError> {
    let mut reader = std::io::BufReader::new(pem);
    let key = rustls_pemfile::private_key(&mut reader)
        .map_err(|e| TransportError::BadIdentity(format!("private key: {e}")))?
        .ok_or_else(|| TransportError::BadIdentity("no private key in PEM".to_string()))?;
    Ok(key)
}

// `SystemTime` not exposed by current rustls API; future-proofing.
#[allow(dead_code)]
fn _unused_systemtime() -> SystemTime {
    SystemTime::now()
}

#[cfg(test)]
mod tests {
    use super::*;
    use rcgen::{CertificateParams, KeyPair, SignatureAlgorithm};

    fn ed25519_identity_and_pin() -> (Identity, String) {
        let key = KeyPair::generate_for(&rcgen::PKCS_ED25519).expect("keypair");
        let params = CertificateParams::new(vec!["test-agent".to_string()]).expect("params");
        let cert = params.self_signed(&key).expect("self-sign");

        let cert_der = cert.der().to_vec();
        let pin = crate::pin::fingerprint_spki_sha256(&cert_der).expect("pin");

        let identity = Identity {
            cert_chain_pem: cert.pem().into_bytes(),
            private_key_pem: key.serialize_pem().into_bytes(),
        };
        (identity, pin)
    }

    #[test]
    fn build_client_config_succeeds_with_ed25519_identity() {
        let (identity, pin) = ed25519_identity_and_pin();
        let cfg = build_client_config(&pin, &identity).expect("config");
        // ALPN must NOT be set here — hyper-rustls installs `h2`
        // when `.enable_http2()` is called by the channel builder.
        assert!(cfg.alpn_protocols.is_empty());
    }

    #[test]
    fn build_client_config_rejects_empty_chain() {
        let (mut identity, pin) = ed25519_identity_and_pin();
        identity.cert_chain_pem = Vec::new();
        match build_client_config(&pin, &identity) {
            Err(TransportError::BadIdentity(_)) => {}
            other => panic!("expected BadIdentity, got {other:?}"),
        }
    }

    #[test]
    fn build_client_config_rejects_garbage_key() {
        let (mut identity, pin) = ed25519_identity_and_pin();
        identity.private_key_pem =
            b"-----BEGIN PRIVATE KEY-----\nGARBAGE\n-----END PRIVATE KEY-----\n".to_vec();
        match build_client_config(&pin, &identity) {
            Err(TransportError::BadIdentity(_)) => {}
            other => panic!("expected BadIdentity, got {other:?}"),
        }
    }

    // Suppress unused-import warning when SignatureAlgorithm unused.
    #[allow(dead_code)]
    fn _keep_sig_algo_in_scope() -> Option<&'static SignatureAlgorithm> {
        None
    }
}
