//! tonic `Channel` builder backed by a custom rustls config.
//!
//! Uses `hyper-rustls` to construct an `HttpsConnector` over our
//! pinned-root [`crate::tls::build_client_config`] output, then hands
//! the connector to tonic via `Channel::builder(...).connect_with_connector`.
//!
//! ## Why we lie to tonic about the URI scheme
//!
//! tonic 0.12 wraps every custom connector in its own TLS gate
//! (`Connector::call` in `tonic::transport::channel::service::connector`):
//! if the URI scheme is `https` AND tonic has no `ClientTlsConfig`,
//! it returns "Connecting to HTTPS without TLS enabled" and refuses to
//! forward the request. tonic's own `ClientTlsConfig` does not allow
//! injecting a custom rustls `ServerCertVerifier` — and our pinned-root
//! verifier is non-negotiable for the daemon trust model.
//!
//! The workaround: present `http://...` to tonic's endpoint so it
//! treats the connection as plaintext, and wrap the underlying
//! hyper-rustls connector in [`ForceHttps`] so the URI scheme is
//! rewritten to `https` *before* the request reaches hyper-rustls.
//! Net effect: tonic is unaware TLS happens, hyper-rustls always
//! TLS-upgrades, and our pinned verifier runs on every handshake.
//!
//! Connection-level tuning:
//!
//! * HTTP/2 keepalive ping every 20 s, timeout 5 s — matches the
//!   server-side gRPC keepalive. Anything tighter risks ping-flood
//!   bans on low-latency proxies.
//! * No HTTP/1.1 fallback: the connector is configured with
//!   `enable_http2()` only.
//! * Domain name parsed once and reused; an invalid endpoint is
//!   refused before the first packet leaves.

use std::task::{Context, Poll};
use std::time::Duration;

use http::uri::{Parts, PathAndQuery, Scheme};
use http::Uri;
use tonic::transport::Channel;
use tower_service::Service;

use crate::{ClientConfig, TransportError};

const KEEPALIVE_INTERVAL: Duration = Duration::from_secs(20);
const KEEPALIVE_TIMEOUT: Duration = Duration::from_secs(5);
const CONNECT_TIMEOUT: Duration = Duration::from_secs(10);

/// Build a connected tonic `Channel` from the given client config.
pub async fn build_channel(config: &ClientConfig) -> Result<Channel, TransportError> {
    let uri: Uri = config
        .endpoint
        .parse()
        .map_err(|e: http::uri::InvalidUri| TransportError::Connect(e.to_string()))?;

    let tls = crate::tls::build_client_config(
        &config.pinned_root_ca_fingerprint_sha256,
        &config.identity,
    )?;

    // hyper-rustls 0.27 requires owned ClientConfig; clone the Arc'd
    // value so the connector takes ownership while callers can keep
    // their reference for diagnostics.
    let tls_config = (*tls).clone();

    let https = hyper_rustls::HttpsConnectorBuilder::new()
        .with_tls_config(tls_config)
        .https_only()
        .enable_http2()
        .build();
    let connector = ForceHttps::new(https);

    // tonic's `Endpoint` validates the URI's scheme on `from_shared`
    // and refuses to forward an `https://` URI through a custom
    // connector unless `tls_config` is also set. Strip the scheme to
    // `http://` here — `ForceHttps` re-applies `https://` when the
    // request is dispatched to hyper-rustls, so the actual wire
    // remains TLS.
    let plain_endpoint = downgrade_scheme_for_tonic(&uri)?;

    let endpoint = tonic::transport::Endpoint::from_shared(plain_endpoint)
        .map_err(|e| TransportError::Connect(e.to_string()))?
        .connect_timeout(CONNECT_TIMEOUT)
        .http2_keep_alive_interval(KEEPALIVE_INTERVAL)
        .keep_alive_timeout(KEEPALIVE_TIMEOUT)
        .keep_alive_while_idle(true)
        .tcp_nodelay(true);

    endpoint
        .connect_with_connector(connector)
        .await
        .map_err(|e| {
            // Walk the error source chain so a generic
            // `tonic::transport::Error` ("transport error") still
            // surfaces the underlying TLS/IO reason.
            let mut chain = vec![e.to_string()];
            let mut src = std::error::Error::source(&e);
            while let Some(inner) = src {
                chain.push(inner.to_string());
                src = inner.source();
            }
            TransportError::Connect(chain.join(": "))
        })
}

/// Return the same authority + port but with the scheme replaced by
/// `http://`, regardless of the input scheme. Tonic's endpoint accepts
/// this and skips its own TLS gate; the [`ForceHttps`] wrapper around
/// the connector promotes back to `https://` before hyper-rustls sees
/// the request.
fn downgrade_scheme_for_tonic(uri: &Uri) -> Result<String, TransportError> {
    let authority = uri
        .authority()
        .ok_or_else(|| TransportError::Connect("endpoint missing authority".to_string()))?;
    Ok(format!("http://{authority}"))
}

/// Wrapper that rewrites every dispatched URI's scheme to `https`
/// before delegating to the inner connector. Used to keep tonic's
/// endpoint plumbing in plaintext mode while routing through
/// hyper-rustls's TLS connector.
#[derive(Clone)]
struct ForceHttps<C> {
    inner: C,
}

impl<C> ForceHttps<C> {
    fn new(inner: C) -> Self {
        Self { inner }
    }
}

impl<C> Service<Uri> for ForceHttps<C>
where
    C: Service<Uri>,
{
    type Response = C::Response;
    type Error = C::Error;
    type Future = C::Future;

    fn poll_ready(&mut self, cx: &mut Context<'_>) -> Poll<Result<(), Self::Error>> {
        self.inner.poll_ready(cx)
    }

    fn call(&mut self, uri: Uri) -> Self::Future {
        let mut parts: Parts = uri.into_parts();
        parts.scheme = Some(Scheme::HTTPS);
        if parts.path_and_query.is_none() {
            parts.path_and_query = Some(PathAndQuery::from_static("/"));
        }
        // Reconstruct: parts is well-formed because we kept authority
        // intact and only swapped scheme + path. A panic here would be
        // a programmer error, not runtime input.
        let upgraded = Uri::from_parts(parts).expect("forced-https uri reconstruct");
        self.inner.call(upgraded)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Identity;

    fn cfg(endpoint: &str) -> ClientConfig {
        ClientConfig {
            endpoint: endpoint.to_string(),
            pinned_root_ca_fingerprint_sha256: "0".repeat(64),
            identity: Identity {
                cert_chain_pem: Vec::new(),
                private_key_pem: Vec::new(),
            },
        }
    }

    #[tokio::test]
    async fn rejects_invalid_uri() {
        let err = build_channel(&cfg("not a uri")).await.unwrap_err();
        match err {
            TransportError::Connect(_) => {}
            other => panic!("expected Connect, got {other:?}"),
        }
    }

    #[tokio::test]
    async fn rejects_empty_identity() {
        let err = build_channel(&cfg("https://example.com:443"))
            .await
            .unwrap_err();
        match err {
            TransportError::BadIdentity(_) => {}
            other => panic!("expected BadIdentity, got {other:?}"),
        }
    }
}
