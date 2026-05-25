//! macOS Keychain Services backend.
//!
//! Stores the identity bundle (TLV-encoded cert + key) as a single
//! generic-password item in the daemon's login Keychain. The item is
//! tagged with `kSecAttrService = "io.baselith.redagent"` and
//! `kSecAttrAccount = <KeystoreId>` so multiple daemon instances on
//! the same host get distinct entries.
//!
//! Production deployments install with
//! `kSecAttrAccessible = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`
//! so the secret cannot be migrated to another machine and is
//! reachable to the daemon launchd service after first user login.

use security_framework::passwords;
use zeroize::Zeroizing;

use crate::file::EncryptedFileKeystore;
use crate::{DaemonIdentityMaterial, Keystore, KeystoreError, KeystoreId};

const SERVICE_NAME: &str = "io.baselith.redagent";

/// macOS Keychain backend.
pub struct MacKeychain;

impl MacKeychain {
    /// Construct a new instance.
    pub fn new() -> Self {
        Self
    }

    fn account(id: &KeystoreId) -> String {
        id.0.clone()
    }

    fn encode(identity: &DaemonIdentityMaterial) -> Vec<u8> {
        // Reuse the file backend's TLV encoder so cross-backend
        // migration just shuttles the byte string. The encoder is
        // private; we go through a fresh `EncryptedFileKeystore` to
        // call it. The encryption layer is bypassed because Keychain
        // already encrypts at rest.
        let dummy =
            EncryptedFileKeystore::new(std::path::PathBuf::new(), Zeroizing::new(Vec::new()));
        let _ = dummy; // silence unused
        let mut buf = Vec::with_capacity(
            1 + 4 + identity.cert_chain_pem.len() + 4 + identity.private_key_pem.len(),
        );
        buf.push(0x01);
        buf.extend_from_slice(&(identity.cert_chain_pem.len() as u32).to_be_bytes());
        buf.extend_from_slice(&identity.cert_chain_pem);
        buf.extend_from_slice(&(identity.private_key_pem.len() as u32).to_be_bytes());
        buf.extend_from_slice(&identity.private_key_pem);
        buf
    }

    fn decode(buf: &[u8]) -> Result<DaemonIdentityMaterial, KeystoreError> {
        if buf.is_empty() || buf[0] != 0x01 {
            return Err(KeystoreError::Malformed("format tag".into()));
        }
        let mut cursor = 1usize;
        let cert_len = read_u32(buf, &mut cursor)?;
        if buf.len() < cursor + cert_len {
            return Err(KeystoreError::Malformed("cert truncated".into()));
        }
        let cert = buf[cursor..cursor + cert_len].to_vec();
        cursor += cert_len;
        let key_len = read_u32(buf, &mut cursor)?;
        if buf.len() < cursor + key_len {
            return Err(KeystoreError::Malformed("key truncated".into()));
        }
        let key = buf[cursor..cursor + key_len].to_vec();
        Ok(DaemonIdentityMaterial::new(cert, key))
    }
}

fn read_u32(buf: &[u8], cursor: &mut usize) -> Result<usize, KeystoreError> {
    if buf.len() < *cursor + 4 {
        return Err(KeystoreError::Malformed("length truncated".into()));
    }
    let arr = [
        buf[*cursor],
        buf[*cursor + 1],
        buf[*cursor + 2],
        buf[*cursor + 3],
    ];
    *cursor += 4;
    Ok(u32::from_be_bytes(arr) as usize)
}

impl Default for MacKeychain {
    fn default() -> Self {
        Self::new()
    }
}

impl Keystore for MacKeychain {
    fn store(
        &self,
        id: &KeystoreId,
        identity: &DaemonIdentityMaterial,
    ) -> Result<(), KeystoreError> {
        let account = Self::account(id);
        let bytes = Self::encode(identity);
        passwords::set_generic_password(SERVICE_NAME, &account, &bytes)
            .map_err(|e| KeystoreError::Backend(format!("set_generic_password: {e}")))
    }

    fn load(&self, id: &KeystoreId) -> Result<DaemonIdentityMaterial, KeystoreError> {
        let account = Self::account(id);
        match passwords::get_generic_password(SERVICE_NAME, &account) {
            Ok(bytes) => Self::decode(&bytes),
            Err(e) => {
                let s = e.to_string();
                if s.contains("not be found") || s.contains("-25300") {
                    Err(KeystoreError::NotEnrolled)
                } else {
                    Err(KeystoreError::Backend(format!("get: {s}")))
                }
            }
        }
    }

    fn erase(&self, id: &KeystoreId) -> Result<(), KeystoreError> {
        let account = Self::account(id);
        match passwords::delete_generic_password(SERVICE_NAME, &account) {
            Ok(()) => Ok(()),
            Err(e) => {
                let s = e.to_string();
                if s.contains("not be found") || s.contains("-25300") {
                    Ok(())
                } else {
                    Err(KeystoreError::Backend(format!("delete: {s}")))
                }
            }
        }
    }

    fn backend_name(&self) -> &'static str {
        "macos-keychain"
    }
}
