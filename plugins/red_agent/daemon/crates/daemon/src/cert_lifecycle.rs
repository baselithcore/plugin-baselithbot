//! Daemon client-cert lifecycle monitor.
//!
//! Parses the leaf cert PEM the daemon presents on every mTLS
//! handshake, extracts its `notAfter`, and surfaces lifecycle events
//! to the backend so an operator can react before the cert expires.
//!
//! Phase 1 surface:
//!
//! * At startup, emit `host.cert.leaf` with the parsed validity
//!   window so the backend records the baseline.
//! * Every heartbeat tick, re-evaluate days-to-expiry and emit:
//!   - `host.cert.expiring_soon` at `WARN` severity ≤ 14 days out;
//!   - `host.cert.expired` at `CRITICAL` once `notAfter < now`.
//!
//! Phase 2 will close the loop with an automatic `RotationRequest`
//! over the gRPC stream when the cert enters the renewal window.

use std::time::SystemTime;

use baselith_redagent_collector as collector;
use baselith_redagent_proto as proto;
use serde_json::json;
use thiserror::Error;
use tracing::warn;
use x509_parser::prelude::*;

const SCHEMA_VERSION: u32 = 1;
/// Days-out that triggers `host.cert.expiring_soon`.
pub const RENEWAL_WINDOW_DAYS: i64 = 14;

/// Errors surfaced when parsing the leaf certificate.
#[derive(Debug, Error)]
pub enum CertError {
    #[error("certificate PEM block missing")]
    MissingPem,
    #[error("certificate parse failed: {0}")]
    Parse(String),
}

/// Lifecycle status returned by [`evaluate`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LifecycleStatus {
    Healthy,
    ExpiringSoon,
    Expired,
}

/// Parsed leaf-cert summary suitable for telemetry attribution.
#[derive(Debug, Clone)]
pub struct LeafSummary {
    pub subject: String,
    pub issuer: String,
    pub serial_hex: String,
    pub not_before_unix: i64,
    pub not_after_unix: i64,
}

/// Extract the leaf certificate from a chain PEM and return its
/// summary. The leaf is assumed to be the first PEM block, matching
/// the order the daemon's keystore writes on enrollment.
pub fn parse_leaf(pem: &[u8]) -> Result<LeafSummary, CertError> {
    let mut iter = Pem::iter_from_buffer(pem);
    let pem_block = iter
        .next()
        .ok_or(CertError::MissingPem)?
        .map_err(|e| CertError::Parse(e.to_string()))?;
    let (_, cert) = X509Certificate::from_der(&pem_block.contents)
        .map_err(|e| CertError::Parse(e.to_string()))?;
    let validity = cert.validity();
    Ok(LeafSummary {
        subject: cert.subject().to_string(),
        issuer: cert.issuer().to_string(),
        serial_hex: hex::encode(cert.tbs_certificate.raw_serial()),
        not_before_unix: validity.not_before.timestamp(),
        not_after_unix: validity.not_after.timestamp(),
    })
}

/// Compute lifecycle status for `summary` against a reference clock.
pub fn evaluate(summary: &LeafSummary, now_unix: i64) -> LifecycleStatus {
    if now_unix >= summary.not_after_unix {
        return LifecycleStatus::Expired;
    }
    let seconds_left = summary.not_after_unix - now_unix;
    if seconds_left < RENEWAL_WINDOW_DAYS * 86_400 {
        LifecycleStatus::ExpiringSoon
    } else {
        LifecycleStatus::Healthy
    }
}

/// Build the lifecycle telemetry event for a given summary + status.
pub fn build_event(
    summary: &LeafSummary,
    status: LifecycleStatus,
    now_unix: i64,
) -> proto::TelemetryEvent {
    let (kind, severity) = match status {
        LifecycleStatus::Healthy => ("host.cert.leaf", proto::Severity::Info),
        LifecycleStatus::ExpiringSoon => ("host.cert.expiring_soon", proto::Severity::High),
        LifecycleStatus::Expired => ("host.cert.expired", proto::Severity::Critical),
    };
    let days_left = (summary.not_after_unix - now_unix).max(0) / 86_400;
    let attrs = json!({
        "schema_version": SCHEMA_VERSION,
        "subject": summary.subject,
        "issuer": summary.issuer,
        "serial_hex": summary.serial_hex,
        "not_before_unix": summary.not_before_unix,
        "not_after_unix": summary.not_after_unix,
        "days_left": days_left,
        "renewal_window_days": RENEWAL_WINDOW_DAYS,
    });
    if !matches!(status, LifecycleStatus::Healthy) {
        warn!(
            kind,
            days_left,
            not_after = summary.not_after_unix,
            "client cert lifecycle warning"
        );
    }
    collector::build_event(kind, severity, attrs)
}

/// Convenience helper: parse + evaluate + build event in one shot.
pub fn observe(pem: &[u8]) -> Result<proto::TelemetryEvent, CertError> {
    let summary = parse_leaf(pem)?;
    let now = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or_default();
    let status = evaluate(&summary, now);
    Ok(build_event(&summary, status, now))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evaluate_healthy_far_future() {
        let s = LeafSummary {
            subject: "CN=test".into(),
            issuer: "CN=ca".into(),
            serial_hex: "00".into(),
            not_before_unix: 0,
            not_after_unix: 4_000_000_000,
        };
        assert_eq!(evaluate(&s, 1_000_000_000), LifecycleStatus::Healthy);
    }

    #[test]
    fn evaluate_expiring_soon() {
        let now = 1_000_000_000_i64;
        let s = LeafSummary {
            subject: "CN=test".into(),
            issuer: "CN=ca".into(),
            serial_hex: "00".into(),
            not_before_unix: 0,
            not_after_unix: now + 5 * 86_400,
        };
        assert_eq!(evaluate(&s, now), LifecycleStatus::ExpiringSoon);
    }

    #[test]
    fn evaluate_expired() {
        let s = LeafSummary {
            subject: "CN=test".into(),
            issuer: "CN=ca".into(),
            serial_hex: "00".into(),
            not_before_unix: 0,
            not_after_unix: 100,
        };
        assert_eq!(evaluate(&s, 1_000_000), LifecycleStatus::Expired);
    }

    #[test]
    fn build_event_kind_matches_status() {
        let s = LeafSummary {
            subject: "CN=test".into(),
            issuer: "CN=ca".into(),
            serial_hex: "00".into(),
            not_before_unix: 0,
            not_after_unix: 4_000_000_000,
        };
        let evt = build_event(&s, LifecycleStatus::Healthy, 1_000_000_000);
        assert_eq!(evt.kind, "host.cert.leaf");
        let evt = build_event(&s, LifecycleStatus::ExpiringSoon, 1_000_000_000);
        assert_eq!(evt.kind, "host.cert.expiring_soon");
        let evt = build_event(&s, LifecycleStatus::Expired, 1_000_000_000);
        assert_eq!(evt.kind, "host.cert.expired");
    }
}
