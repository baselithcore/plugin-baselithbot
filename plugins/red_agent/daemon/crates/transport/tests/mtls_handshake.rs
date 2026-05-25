//! End-to-end mTLS handshake harness for the transport client.
//!
//! Boots an in-process tonic `AgentChannel` server bound to a random
//! loopback port, issues a tiny PKI rooted at an ed25519 CA, and drives
//! the production [`baselith_redagent_transport::Client`] through a
//! full handshake. Asserts:
//!
//! 1. **Happy path** — pin matches the CA's SPKI, the client receives a
//!    `ServerHello` over the bidirectional stream.
//! 2. **Negative pin** — wrong fingerprint causes the TLS handshake to
//!    fail closed; no stream is established.
//!
//! These checks are the regression net for M2: any change to TLS
//! parameters, pin verifier, or rustls provider that breaks the
//! daemon ↔ backend handshake will be caught before release.
//!
//! The harness is process-local and deterministic so it runs in CI
//! without docker — `testcontainers`-style isolation comes from the
//! random port + per-test PKI, not from a container.

use std::net::SocketAddr;
use std::pin::Pin;
use std::time::Duration;

use baselith_redagent_proto as proto;
use baselith_redagent_proto::v1::agent_channel_server::{AgentChannel, AgentChannelServer};
use baselith_redagent_transport::pin::fingerprint_spki_sha256;
use baselith_redagent_transport::{Client, ClientConfig, Identity};
use prost_types::Timestamp;
use rcgen::{CertificateParams, DnType, KeyPair, KeyUsagePurpose, SanType, PKCS_ED25519};
use tokio::net::TcpListener;
use tokio::sync::mpsc;
use tokio_stream::wrappers::{ReceiverStream, TcpListenerStream};
use tokio_stream::{Stream, StreamExt};
use tonic::transport::server::TcpIncoming;
use tonic::transport::{Identity as TonicIdentity, Server, ServerTlsConfig};
use tonic::{Request, Response, Status, Streaming};

const HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(5);

/// Materials produced by [`build_pki`] — everything the test server
/// and client need to negotiate a pinned-root mTLS session.
struct Pki {
    /// CA cert chain in PEM. Used as the server's chain (leaf + root)
    /// and as the client's trust anchor (`client_ca_root`).
    server_chain_pem: String,
    /// Server private key (ed25519 PKCS#8, PEM).
    server_key_pem: String,
    /// CA cert PEM only — supplied to tonic as `client_ca_root` so the
    /// server validates the daemon's client cert against the same CA.
    ca_pem: String,
    /// Daemon-side client identity (cert chain + key) in PEM.
    client_identity: Identity,
    /// SPKI SHA-256 fingerprint of the CA cert. The daemon pins this
    /// at install time; the verifier walks the presented chain looking
    /// for a match.
    ca_pin_hex: String,
}

/// Build a minimal three-cert PKI: an ed25519 CA, a server leaf signed
/// by the CA (SAN = `localhost`), and a client leaf signed by the CA
/// (SAN URI = SPIFFE-style daemon ID).
fn build_pki() -> Pki {
    // --- CA ---------------------------------------------------------
    let ca_key = KeyPair::generate_for(&PKCS_ED25519).expect("ca keypair");
    let mut ca_params = CertificateParams::new(Vec::new()).expect("ca params");
    ca_params
        .distinguished_name
        .push(DnType::CommonName, "BaselithRedAgentTestCA");
    ca_params.is_ca = rcgen::IsCa::Ca(rcgen::BasicConstraints::Unconstrained);
    ca_params.key_usages = vec![
        KeyUsagePurpose::KeyCertSign,
        KeyUsagePurpose::CrlSign,
        KeyUsagePurpose::DigitalSignature,
    ];
    let ca_cert = ca_params.self_signed(&ca_key).expect("ca self-sign");
    let ca_pem = ca_cert.pem();
    let ca_der = ca_cert.der().to_vec();
    let ca_pin_hex = fingerprint_spki_sha256(&ca_der).expect("ca pin");

    // --- Server leaf -----------------------------------------------
    let server_key = KeyPair::generate_for(&PKCS_ED25519).expect("server keypair");
    let mut server_params =
        CertificateParams::new(vec!["localhost".to_string()]).expect("server params");
    server_params
        .distinguished_name
        .push(DnType::CommonName, "test-backend.localhost");
    server_params.subject_alt_names = vec![SanType::DnsName(
        rcgen::Ia5String::try_from("localhost").expect("dns san"),
    )];
    server_params.key_usages = vec![
        KeyUsagePurpose::DigitalSignature,
        KeyUsagePurpose::KeyEncipherment,
    ];
    server_params.extended_key_usages = vec![rcgen::ExtendedKeyUsagePurpose::ServerAuth];
    let server_cert = server_params
        .signed_by(&server_key, &ca_cert, &ca_key)
        .expect("server sign");
    let server_chain_pem = format!("{}{}", server_cert.pem(), ca_pem);
    let server_key_pem = server_key.serialize_pem();

    // --- Client (daemon) leaf --------------------------------------
    let client_key = KeyPair::generate_for(&PKCS_ED25519).expect("client keypair");
    let mut client_params = CertificateParams::new(Vec::new()).expect("client params");
    client_params
        .distinguished_name
        .push(DnType::CommonName, "test-daemon");
    client_params.subject_alt_names = vec![SanType::URI(
        rcgen::Ia5String::try_from(
            "spiffe://baselith.local/tenant/test/agent/00000000-0000-0000-0000-000000000001",
        )
        .expect("uri san"),
    )];
    client_params.key_usages = vec![KeyUsagePurpose::DigitalSignature];
    client_params.extended_key_usages = vec![rcgen::ExtendedKeyUsagePurpose::ClientAuth];
    let client_cert = client_params
        .signed_by(&client_key, &ca_cert, &ca_key)
        .expect("client sign");

    Pki {
        server_chain_pem,
        server_key_pem,
        ca_pem: ca_pem.clone(),
        client_identity: Identity {
            cert_chain_pem: client_cert.pem().into_bytes(),
            private_key_pem: client_key.serialize_pem().into_bytes(),
        },
        ca_pin_hex,
    }
}

/// Trivial AgentChannel that consumes one `AgentHello` and replies
/// with a single `ServerHello`. The handshake is the only thing this
/// harness needs to verify.
#[derive(Default)]
struct StubAgentChannel;

#[tonic::async_trait]
impl AgentChannel for StubAgentChannel {
    type OpenStreamStream =
        Pin<Box<dyn Stream<Item = Result<proto::ServerMessage, Status>> + Send + 'static>>;

    async fn open_stream(
        &self,
        request: Request<Streaming<proto::AgentMessage>>,
    ) -> Result<Response<Self::OpenStreamStream>, Status> {
        let mut inbound = request.into_inner();

        // Wait for the daemon's hello before we reply, so the test
        // proves both directions of the stream are wired correctly.
        let first = inbound
            .next()
            .await
            .ok_or_else(|| Status::aborted("stream closed before hello"))?
            .map_err(|e| Status::internal(format!("inbound error: {e}")))?;
        let _hello = match first.payload {
            Some(proto::v1::agent_message::Payload::Hello(h)) => h,
            other => {
                return Err(Status::invalid_argument(format!(
                    "expected AgentHello, got {other:?}"
                )));
            }
        };

        let (tx, rx) = mpsc::channel::<Result<proto::ServerMessage, Status>>(2);
        let server_hello = proto::ServerMessage {
            seq: 1,
            nonce: vec![0_u8; 16],
            ts: Some(Timestamp {
                seconds: 0,
                nanos: 0,
            }),
            payload: Some(proto::v1::server_message::Payload::Hello(
                proto::ServerHello {
                    protocol_version_min: 1,
                    capabilities: Vec::new(),
                    heartbeat_interval: Some(prost_types::Duration {
                        seconds: 30,
                        nanos: 0,
                    }),
                    telemetry_batch_max: 32,
                    message_size_max_bytes: 1_048_576,
                    tenant_id_echo: "test".into(),
                },
            )),
        };
        tx.send(Ok(server_hello))
            .await
            .map_err(|e| Status::internal(format!("send hello: {e}")))?;
        // Drop tx so the server stream completes; the daemon will see
        // the stream close, which is fine for this handshake test.
        Ok(Response::new(Box::pin(ReceiverStream::new(rx))))
    }
}

/// Bind a tonic server on a random loopback port and return the
/// assigned address plus a join handle. The server lives until the
/// returned shutdown sender fires.
async fn spawn_server(pki: &Pki) -> (SocketAddr, tokio::sync::oneshot::Sender<()>) {
    let identity = TonicIdentity::from_pem(&pki.server_chain_pem, &pki.server_key_pem);
    let client_ca = tonic::transport::Certificate::from_pem(&pki.ca_pem);
    let tls = ServerTlsConfig::new()
        .identity(identity)
        .client_ca_root(client_ca);

    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("local addr");
    let incoming = TcpIncoming::from_listener(listener, true, None).expect("incoming");

    let (shutdown_tx, shutdown_rx) = tokio::sync::oneshot::channel::<()>();
    let svc = AgentChannelServer::new(StubAgentChannel);

    tokio::spawn(async move {
        let result = Server::builder()
            .tls_config(tls)
            .expect("tls config")
            .add_service(svc)
            .serve_with_incoming_shutdown(incoming, async {
                let _ = shutdown_rx.await;
            })
            .await;
        if let Err(e) = result {
            eprintln!("server exited with error: {e}");
        }
    });

    // Tiny grace window for the server to start listening on TLS.
    tokio::time::sleep(Duration::from_millis(50)).await;
    (addr, shutdown_tx)
}

fn agent_hello() -> proto::AgentMessage {
    proto::AgentMessage {
        seq: 1,
        nonce: vec![0_u8; 16],
        ts: Some(Timestamp {
            seconds: 0,
            nanos: 0,
        }),
        payload: Some(proto::v1::agent_message::Payload::Hello(
            proto::AgentHello {
                protocol_version: 1,
                daemon_version: "0.0.0-test".into(),
                agent_uuid: "00000000-0000-0000-0000-000000000001".into(),
                platform: None,
                capabilities: Vec::new(),
                last_acked_server_seq: 0,
            },
        )),
    }
}

fn init_tracing() {
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("off")),
        )
        .with_test_writer()
        .try_init();
}

#[tokio::test]
async fn handshake_succeeds_with_pinned_root() {
    init_tracing();
    let pki = build_pki();
    let (addr, shutdown) = spawn_server(&pki).await;

    let cfg = ClientConfig {
        endpoint: format!("https://localhost:{}", addr.port()),
        pinned_root_ca_fingerprint_sha256: pki.ca_pin_hex.clone(),
        identity: pki.client_identity.clone(),
    };

    let client = tokio::time::timeout(HANDSHAKE_TIMEOUT, Client::connect(&cfg))
        .await
        .expect("connect timed out")
        .expect("connect failed");

    // Drive a single round-trip: send AgentHello, receive ServerHello.
    let (tx, rx) = mpsc::channel::<proto::AgentMessage>(2);
    tx.send(agent_hello()).await.expect("send hello");
    let request = tonic::Request::new(ReceiverStream::new(rx));
    let mut inner = client.into_inner();
    let response = tokio::time::timeout(HANDSHAKE_TIMEOUT, inner.open_stream(request))
        .await
        .expect("open_stream timeout")
        .expect("open_stream rpc");

    let mut server_stream = response.into_inner();
    let first = tokio::time::timeout(HANDSHAKE_TIMEOUT, server_stream.message())
        .await
        .expect("server hello timeout")
        .expect("server hello rpc")
        .expect("server hello payload");

    match first.payload {
        Some(proto::v1::server_message::Payload::Hello(h)) => {
            assert_eq!(h.protocol_version_min, 1);
            assert_eq!(h.tenant_id_echo, "test");
        }
        other => panic!("expected ServerHello, got {other:?}"),
    }

    // Drop the request channel to signal stream close, then shut down.
    drop(tx);
    let _ = shutdown.send(());
}

#[tokio::test]
async fn handshake_fails_with_wrong_pin() {
    init_tracing();
    let pki = build_pki();
    let (addr, shutdown) = spawn_server(&pki).await;

    let bogus_pin = "0".repeat(64);
    let cfg = ClientConfig {
        endpoint: format!("https://localhost:{}", addr.port()),
        pinned_root_ca_fingerprint_sha256: bogus_pin,
        identity: pki.client_identity.clone(),
    };

    // The TLS handshake must fail closed; we don't care which error
    // variant the transport surfaces, only that no Client is built.
    let result = tokio::time::timeout(HANDSHAKE_TIMEOUT, Client::connect(&cfg)).await;
    match result {
        Ok(Err(_)) => {}
        Ok(Ok(_)) => panic!("connect succeeded with bogus pin — pin verifier bypassed"),
        Err(_) => panic!("connect hung instead of failing closed"),
    }
    let _ = shutdown.send(());
}

// Suppress unused-import warning when individual variants change.
#[allow(dead_code)]
fn _stream_marker() -> Option<TcpListenerStream> {
    None
}
