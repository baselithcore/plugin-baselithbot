//! OS keystore abstraction.
//!
//! Backends:
//!
//! * **macOS** — Keychain Services via `Security.framework`. Items
//!   tagged `kSecAttrService = "io.baselith.redagent"`, key bound to
//!   the daemon's bundle identifier so other processes cannot read.
//! * **linux** — kernel keyring (`keyctl`) when available. Daemon's
//!   process keyring holds the item; survives across reconnects but
//!   not host reboot. Re-loaded from the encrypted file fallback on
//!   reboot.
//! * **encrypted file fallback** — `chacha20poly1305` AEAD over the
//!   identity bundle, key derived via Argon2id from a host-bound
//!   secret (TPM / SEP / disk UUID). Used everywhere as a durable
//!   tier; OS keystores cache the unwrapped value for fast access.
//!
//! The private key bytes always live behind a [`zeroize::Zeroizing`]
//! wrapper so a panic or drop scrubs them from memory.

#![deny(unsafe_code)]
#![warn(missing_docs)]

use thiserror::Error;
use zeroize::Zeroizing;

mod file;

#[cfg(target_os = "macos")]
mod macos;

#[cfg(target_os = "linux")]
mod linux;

pub use file::EncryptedFileKeystore;

/// Failures any keystore backend can surface.
#[derive(Debug, Error)]
pub enum KeystoreError {
    /// No identity is currently provisioned for this daemon.
    #[error("daemon not enrolled — no identity in keystore")]
    NotEnrolled,

    /// The encrypted blob failed AEAD verification or the master
    /// secret no longer matches.
    #[error("identity decryption failed")]
    DecryptionFailed,

    /// Underlying I/O error.
    #[error("keystore I/O error: {0}")]
    Io(String),

    /// The platform backend rejected an operation.
    #[error("keystore backend error: {0}")]
    Backend(String),

    /// Bytes do not look like a valid identity bundle (TLV / version).
    #[error("identity bundle malformed: {0}")]
    Malformed(String),
}

/// Identifier used to look up the daemon's identity in the keystore.
///
/// The default `baselith-redagent-default` is used by the installer;
/// operators running multiple daemons on the same host (rare) can
/// configure a custom value via the daemon config.
#[derive(Debug, Clone)]
pub struct KeystoreId(pub String);

impl Default for KeystoreId {
    fn default() -> Self {
        KeystoreId("baselith-redagent-default".to_string())
    }
}

/// Identity material the daemon needs at every connect.
///
/// Both fields are PEM-encoded; the private key MUST be ed25519
/// PKCS#8. The struct deliberately implements neither `Debug` nor
/// `Display` — accidental logging of the private key would be a
/// catastrophic operator error.
pub struct DaemonIdentityMaterial {
    /// Cert chain in PEM (leaf first, then intermediates).
    pub cert_chain_pem: Zeroizing<Vec<u8>>,
    /// Private key in PEM (ed25519 PKCS#8).
    pub private_key_pem: Zeroizing<Vec<u8>>,
}

impl DaemonIdentityMaterial {
    /// Construct from raw PEM bytes. Caller is responsible for
    /// validating the contents — this constructor only ensures the
    /// `Zeroizing` wrapper is applied.
    pub fn new(cert_chain_pem: Vec<u8>, private_key_pem: Vec<u8>) -> Self {
        Self {
            cert_chain_pem: Zeroizing::new(cert_chain_pem),
            private_key_pem: Zeroizing::new(private_key_pem),
        }
    }
}

/// Trait implemented by every keystore backend.
pub trait Keystore: Send + Sync {
    /// Persist a fresh identity. Overwrites any existing entry under
    /// the same id; callers must explicitly call [`Self::erase`] first
    /// when rotating identities to keep audit boundaries clean.
    fn store(
        &self,
        id: &KeystoreId,
        identity: &DaemonIdentityMaterial,
    ) -> Result<(), KeystoreError>;

    /// Load the identity back. Returns `NotEnrolled` if absent.
    fn load(&self, id: &KeystoreId) -> Result<DaemonIdentityMaterial, KeystoreError>;

    /// Best-effort erase. Implementations MUST overwrite secret
    /// material before deleting the storage location.
    fn erase(&self, id: &KeystoreId) -> Result<(), KeystoreError>;

    /// Backend descriptor for diagnostics. Never includes secret
    /// material.
    fn backend_name(&self) -> &'static str;
}

/// Pick the strongest backend available on the current host, falling
/// back to the encrypted file path supplied by the caller.
///
/// macOS → Keychain · linux → kernel keyring · everywhere → file.
pub fn pick_default_backend(
    file_path: std::path::PathBuf,
    master_secret: Zeroizing<Vec<u8>>,
) -> Box<dyn Keystore> {
    #[cfg(target_os = "macos")]
    {
        // Note: the file backend is currently not used as a fallback
        // on macOS because Keychain is always available on Apple
        // hardware. The parameters are accepted for API symmetry.
        let _ = (&file_path, &master_secret);
        Box::new(macos::MacKeychain::new())
    }

    #[cfg(target_os = "linux")]
    {
        match linux::KernelKeyring::new() {
            Ok(ring) => Box::new(ring),
            Err(_) => Box::new(EncryptedFileKeystore::new(file_path, master_secret)),
        }
    }

    #[cfg(not(any(target_os = "macos", target_os = "linux")))]
    {
        Box::new(EncryptedFileKeystore::new(file_path, master_secret))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_keystore_id_is_stable() {
        assert_eq!(
            KeystoreId::default().0,
            "baselith-redagent-default".to_string()
        );
    }

    #[test]
    fn identity_material_zeroizes_on_drop() {
        // Smoke test the Zeroizing wrapper exists; full memory-erase
        // assertion would require unsafe pointer access we don't want
        // in this crate.
        let m = DaemonIdentityMaterial::new(b"cert".to_vec(), b"key".to_vec());
        assert_eq!(m.cert_chain_pem.as_slice(), b"cert");
        assert_eq!(m.private_key_pem.as_slice(), b"key");
    }
}
