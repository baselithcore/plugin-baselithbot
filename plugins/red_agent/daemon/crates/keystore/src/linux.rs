//! Linux kernel keyring backend.
//!
//! Stores the identity bundle in the daemon's process keyring
//! (`KEY_SPEC_PROCESS_KEYRING`) so secrets are accessible only to
//! the running daemon and its descendants. The keyring is volatile —
//! cleared at reboot — so the daemon also persists to the encrypted
//! file backend; on startup it tries the keyring first, then the
//! file, and re-populates the keyring after a successful file load.

use linux_keyutils::{KeyRing, KeyRingIdentifier};

use crate::{DaemonIdentityMaterial, Keystore, KeystoreError, KeystoreId};

/// Linux kernel keyring backend.
pub struct KernelKeyring {
    ring: KeyRing,
}

impl KernelKeyring {
    /// Open the daemon's process keyring. Returns an error if the
    /// keyring subsystem is unavailable (containers / minimal envs).
    pub fn new() -> Result<Self, KeystoreError> {
        KeyRing::from_special_id(KeyRingIdentifier::Process, true)
            .map(|ring| Self { ring })
            .map_err(|e| KeystoreError::Backend(format!("keyring open: {e:?}")))
    }

    fn description(id: &KeystoreId) -> String {
        format!("baselith.redagent.{}", id.0)
    }

    fn encode(identity: &DaemonIdentityMaterial) -> Vec<u8> {
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

impl Keystore for KernelKeyring {
    fn store(
        &self,
        id: &KeystoreId,
        identity: &DaemonIdentityMaterial,
    ) -> Result<(), KeystoreError> {
        let bytes = Self::encode(identity);
        self.ring
            .add_key(&Self::description(id), &bytes)
            .map(|_| ())
            .map_err(|e| KeystoreError::Backend(format!("add_key: {e:?}")))
    }

    fn load(&self, id: &KeystoreId) -> Result<DaemonIdentityMaterial, KeystoreError> {
        let key = self
            .ring
            .search(&Self::description(id))
            .map_err(|_| KeystoreError::NotEnrolled)?;
        let mut buf = vec![0u8; 64 * 1024];
        let n = key
            .read(&mut buf)
            .map_err(|e| KeystoreError::Backend(format!("read: {e:?}")))?;
        Self::decode(&buf[..n])
    }

    fn erase(&self, id: &KeystoreId) -> Result<(), KeystoreError> {
        match self.ring.search(&Self::description(id)) {
            Ok(key) => key
                .invalidate()
                .map_err(|e| KeystoreError::Backend(format!("invalidate: {e:?}"))),
            Err(_) => Ok(()),
        }
    }

    fn backend_name(&self) -> &'static str {
        "linux-kernel-keyring"
    }
}
