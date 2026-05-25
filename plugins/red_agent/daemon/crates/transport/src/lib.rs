//! mTLS gRPC transport for the daemon ↔ backend `AgentChannel` stream.
//!
//! Phase 1 surface: a [`Client`] that opens a single bidirectional
//! stream over TLS 1.3 with an ed25519 client cert and a pinned root
//! CA fingerprint. Reconnect / backoff lives in the `daemon` crate so
//! this layer stays purely transport.
//!
//! Trust invariants:
//!
//! * The server's cert chain MUST chain to the pinned root CA whose
//!   SHA-256 fingerprint was baked into the agent at install time.
//!   Any chain that validates against the system trust store but not
//!   our pin is rejected.
//! * TLS 1.3 only. No fallback negotiation, no compression, no early
//!   data. The daemon refuses to connect over anything weaker.
//! * The private key never crosses this crate's boundary in plaintext;
//!   it is loaded from the keystore by callers and zeroized on drop.

#![deny(unsafe_code)]
#![warn(missing_docs)]

pub mod channel;
pub mod pin;
pub mod tls;

use thiserror::Error;

/// Errors a transport open / connect can produce.
#[derive(Debug, Error)]
pub enum TransportError {
    /// The pinned root CA fingerprint did not match the server chain.
    #[error("root CA fingerprint pin mismatch")]
    PinMismatch,

    /// The supplied cert / key material was malformed.
    #[error("identity material invalid: {0}")]
    BadIdentity(String),

    /// The TLS handshake failed for a reason other than pin mismatch.
    #[error("TLS handshake failed: {0}")]
    Tls(String),

    /// The gRPC channel could not be established.
    #[error("gRPC connect failed: {0}")]
    Connect(String),
}

/// Identity material the daemon needs to present at TLS handshake.
///
/// PEM-encoded; the private key MUST be ed25519 PKCS#8.
#[derive(Debug, Clone)]
pub struct Identity {
    /// Leaf cert chain in PEM (leaf first, then intermediates).
    pub cert_chain_pem: Vec<u8>,
    /// Private key in PEM (ed25519 PKCS#8).
    pub private_key_pem: Vec<u8>,
}

/// Configuration accepted by [`Client::connect`].
#[derive(Debug, Clone)]
pub struct ClientConfig {
    /// gRPC backend endpoint, e.g. `https://red-agent.example.com:443`.
    pub endpoint: String,
    /// SHA-256 fingerprint of the pinned root CA, lowercase hex.
    pub pinned_root_ca_fingerprint_sha256: String,
    /// Identity material for client mTLS.
    pub identity: Identity,
}

/// Connected gRPC client over an mTLS-pinned channel.
///
/// Wraps the generated tonic `AgentChannelClient` so the daemon
/// runtime opens at most one stream per agent and never re-instantiates
/// the underlying `tonic::transport::Channel` (HTTP/2 multiplexing
/// keeps the same TLS session across reconnect attempts within the
/// same channel handle).
pub struct Client {
    inner: baselith_redagent_proto::AgentChannelClient<tonic::transport::Channel>,
}

impl Client {
    /// Build a connected client given the endpoint and identity.
    ///
    /// On success the channel is open but no RPC has been issued yet;
    /// the caller drives the bidirectional stream via
    /// [`Self::open_stream`].
    pub async fn connect(config: &ClientConfig) -> Result<Self, TransportError> {
        let channel = channel::build_channel(config).await?;
        let inner = baselith_redagent_proto::AgentChannelClient::new(channel);
        Ok(Self { inner })
    }

    /// Access the underlying tonic client for streaming RPCs.
    pub fn into_inner(
        self,
    ) -> baselith_redagent_proto::AgentChannelClient<tonic::transport::Channel> {
        self.inner
    }
}
