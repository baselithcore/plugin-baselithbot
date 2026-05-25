//! Daemon enrollment subcommand.
//!
//! Implements the client side of the
//! `POST /red-agent/agents/enroll` REST endpoint. Flow:
//!
//! 1. Generate ed25519 keypair on-device. Private key never leaves
//!    this process before being persisted to the keystore.
//! 2. Build a CSR carrying only the public key (no SAN / EKU /
//!    BasicConstraints — the issuer is authoritative).
//! 3. POST CSR + agent_uuid + platform metadata + bearer token.
//! 4. On success, persist the resulting cert + private key to the
//!    keystore. The plaintext token is discarded immediately and
//!    never written to disk.
//!
//! Failure modes the caller should expect:
//!
//! * `401 unauthorized` — token invalid / expired / already redeemed.
//! * `400 bad request` — CSR malformed or rejected by server policy.
//! * `503 service unavailable` — server-side CA not configured.

use anyhow::{Context, Result};
use baselith_redagent_keystore::{DaemonIdentityMaterial, Keystore, KeystoreId};
use ed25519_dalek::pkcs8::EncodePrivateKey;
use ed25519_dalek::SigningKey;
use rand::rngs::OsRng;
use rand::RngCore;
use serde::{Deserialize, Serialize};
use tracing::{info, warn};
use uuid::Uuid;
use zeroize::Zeroizing;

use crate::csr::build_csr_pem;
use crate::platform::PlatformInfo;
use crate::Config;

#[derive(Debug, Serialize)]
struct EnrollmentRequest {
    enrollment_token: String,
    agent_uuid: String,
    csr_pem: String,
    daemon_version: String,
    protocol_version: u32,
    os: &'static str,
    os_version: String,
    kernel_version: String,
    arch: String,
    hostname: String,
    boot_id: String,
    cpu_count: u64,
    mem_total_bytes: u64,
    declared_capabilities: Vec<&'static str>,
}

#[derive(Debug, Deserialize)]
struct EnrollmentResponse {
    agent_uuid: String,
    tenant_id: String,
    cert_pem: String,
    chain_pem: String,
    not_after: String,
    spiffe_uri: String,
    backend_grpc_endpoint: String,
    root_ca_fingerprint_sha256: String,
}

/// Run the enroll subcommand against the configured backend.
pub async fn run(
    config: &Config,
    token: Zeroizing<String>,
    keystore: &dyn Keystore,
    daemon_version: &str,
    enroll_endpoint: &str,
) -> Result<()> {
    info!(endpoint = enroll_endpoint, "starting enrollment");

    let agent_uuid = Uuid::new_v4();
    let mut secret = [0u8; 32];
    OsRng.fill_bytes(&mut secret);
    let signing_key = SigningKey::from_bytes(&secret);
    let csr_pem = build_csr_pem(&signing_key, agent_uuid)?;

    let platform = PlatformInfo::probe();
    let body = EnrollmentRequest {
        enrollment_token: token.as_str().to_string(),
        agent_uuid: agent_uuid.to_string(),
        csr_pem: csr_pem.clone(),
        daemon_version: daemon_version.to_string(),
        protocol_version: config.protocol_version,
        os: os_str(platform.os),
        os_version: platform.os_version,
        kernel_version: platform.kernel_version,
        arch: platform.arch,
        hostname: platform.hostname,
        boot_id: platform.boot_id,
        cpu_count: platform.cpu_count,
        mem_total_bytes: platform.mem_total_bytes,
        declared_capabilities: declared_capability_names(),
    };

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .context("build http client")?;

    let response = client
        .post(enroll_endpoint)
        .json(&body)
        .send()
        .await
        .context("POST /agents/enroll")?;

    if !response.status().is_success() {
        let status = response.status();
        let text = response.text().await.unwrap_or_default();
        anyhow::bail!("enrollment rejected: {status}: {text}");
    }

    let issued: EnrollmentResponse = response
        .json()
        .await
        .context("decode enrollment response")?;

    info!(
        spiffe_uri = %issued.spiffe_uri,
        not_after = %issued.not_after,
        backend_grpc = %issued.backend_grpc_endpoint,
        tenant = %issued.tenant_id,
        "received signed cert"
    );

    let private_key_pem = signing_key
        .to_pkcs8_pem(ed25519_dalek::pkcs8::spki::der::pem::LineEnding::LF)
        .context("encode private key PEM")?
        .as_bytes()
        .to_vec();

    let chain = format!("{}{}", issued.cert_pem, issued.chain_pem);
    let identity = DaemonIdentityMaterial::new(chain.into_bytes(), private_key_pem);

    keystore
        .store(&KeystoreId(config.keystore_id.clone()), &identity)
        .map_err(|e| anyhow::anyhow!("persist identity: {e}"))?;

    // Persist the pinned root fingerprint next to the daemon's config
    // so the runtime path can pick it up on next start. The fingerprint
    // is public information; it just gates which CA chain is trusted.
    if let Err(e) = std::fs::write(
        &config.root_ca_fingerprint_path,
        issued.root_ca_fingerprint_sha256.trim(),
    ) {
        warn!(error = %e, "could not persist pinned fingerprint; user must do it manually");
    }

    info!(
        agent_uuid = %issued.agent_uuid,
        "enrollment complete; daemon ready to run"
    );
    Ok(())
}

fn os_str(os: baselith_redagent_proto::v1::platform::Os) -> &'static str {
    use baselith_redagent_proto::v1::platform::Os;
    match os {
        Os::Linux => "linux",
        Os::Macos => "macos",
        Os::Windows => "windows",
        Os::Unspecified => "linux", // server schema requires a value
    }
}

fn declared_capability_names() -> Vec<&'static str> {
    vec![
        "CAPABILITY_PROC_INVENTORY",
        "CAPABILITY_PKG_INVENTORY",
        "CAPABILITY_FILE_HASH",
        "CAPABILITY_NET_LISTEN",
        "CAPABILITY_USER_INVENTORY",
    ]
}
