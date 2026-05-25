//! Encrypted-file keystore backend.
//!
//! Layout on disk:
//!
//! ```text
//! [16 bytes salt][12 bytes nonce][N bytes ciphertext]
//! ```
//!
//! * Master secret is **not** stored on disk; it is bound to a host
//!   secret (TPM / SEP / disk UUID) supplied by the daemon config.
//! * Argon2id derives a 32-byte key from `(salt, master_secret)`.
//! * `chacha20poly1305` AEAD provides confidentiality + integrity.
//!   Tampering with the file fails decryption rather than producing
//!   garbage output.
//! * The plaintext bundle is a 4-byte big-endian length followed by
//!   the cert chain PEM, then a 4-byte big-endian length followed by
//!   the private key PEM. Versioned by a 1-byte tag at the start so
//!   future format changes can be detected without ambiguity.

use std::fs;
use std::io::Write;
use std::path::PathBuf;

use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::aead::{Aead, KeyInit};
use chacha20poly1305::{ChaCha20Poly1305, Key, Nonce};
use rand::RngCore;
use zeroize::Zeroizing;

use crate::{DaemonIdentityMaterial, Keystore, KeystoreError, KeystoreId};

const SALT_LEN: usize = 16;
const NONCE_LEN: usize = 12;
const KEY_LEN: usize = 32;
const FORMAT_TAG: u8 = 0x01;

/// File-backed keystore using ChaCha20-Poly1305 + Argon2id.
pub struct EncryptedFileKeystore {
    base_path: PathBuf,
    master_secret: Zeroizing<Vec<u8>>,
}

impl EncryptedFileKeystore {
    /// Create a new instance. The directory is created on first
    /// `store` call; we do not pre-create it so a misconfigured
    /// path surfaces an error at write time rather than at startup.
    pub fn new(base_path: PathBuf, master_secret: Zeroizing<Vec<u8>>) -> Self {
        Self {
            base_path,
            master_secret,
        }
    }

    fn path_for(&self, id: &KeystoreId) -> PathBuf {
        self.base_path.join(format!("{}.identity", id.0))
    }

    fn derive_key(&self, salt: &[u8]) -> Result<Zeroizing<[u8; KEY_LEN]>, KeystoreError> {
        let mut key = Zeroizing::new([0u8; KEY_LEN]);
        let params = Params::new(64 * 1024, 3, 1, Some(KEY_LEN))
            .map_err(|e| KeystoreError::Backend(format!("argon2 params: {e}")))?;
        let argon = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
        argon
            .hash_password_into(&self.master_secret, salt, key.as_mut_slice())
            .map_err(|e| KeystoreError::Backend(format!("argon2: {e}")))?;
        Ok(key)
    }

    fn encode_plaintext(identity: &DaemonIdentityMaterial) -> Vec<u8> {
        let mut buf = Vec::with_capacity(
            1 + 4 + identity.cert_chain_pem.len() + 4 + identity.private_key_pem.len(),
        );
        buf.push(FORMAT_TAG);
        buf.extend_from_slice(&(identity.cert_chain_pem.len() as u32).to_be_bytes());
        buf.extend_from_slice(&identity.cert_chain_pem);
        buf.extend_from_slice(&(identity.private_key_pem.len() as u32).to_be_bytes());
        buf.extend_from_slice(&identity.private_key_pem);
        buf
    }

    fn decode_plaintext(buf: &[u8]) -> Result<DaemonIdentityMaterial, KeystoreError> {
        if buf.is_empty() || buf[0] != FORMAT_TAG {
            return Err(KeystoreError::Malformed(
                "format tag mismatch or empty".into(),
            ));
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

impl Keystore for EncryptedFileKeystore {
    fn store(
        &self,
        id: &KeystoreId,
        identity: &DaemonIdentityMaterial,
    ) -> Result<(), KeystoreError> {
        let path = self.path_for(id);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|e| KeystoreError::Io(e.to_string()))?;
        }

        let mut salt = [0u8; SALT_LEN];
        let mut nonce_bytes = [0u8; NONCE_LEN];
        rand::thread_rng().fill_bytes(&mut salt);
        rand::thread_rng().fill_bytes(&mut nonce_bytes);

        let key = self.derive_key(&salt)?;
        let cipher = ChaCha20Poly1305::new(Key::from_slice(key.as_slice()));
        let plaintext = Self::encode_plaintext(identity);
        let nonce = Nonce::from_slice(&nonce_bytes);
        let ciphertext = cipher
            .encrypt(nonce, plaintext.as_ref())
            .map_err(|e| KeystoreError::Backend(format!("encrypt: {e}")))?;

        let mut out = Vec::with_capacity(SALT_LEN + NONCE_LEN + ciphertext.len());
        out.extend_from_slice(&salt);
        out.extend_from_slice(&nonce_bytes);
        out.extend_from_slice(&ciphertext);

        let tmp = path.with_extension("identity.tmp");
        {
            let mut f = fs::File::create(&tmp)
                .map_err(|e| KeystoreError::Io(format!("create tmp: {e}")))?;
            f.write_all(&out)
                .map_err(|e| KeystoreError::Io(format!("write tmp: {e}")))?;
            f.sync_all()
                .map_err(|e| KeystoreError::Io(format!("fsync: {e}")))?;
        }
        fs::rename(&tmp, &path).map_err(|e| KeystoreError::Io(format!("rename: {e}")))?;

        // Tighten POSIX permissions to 0600 on Unix; Windows users
        // rely on filesystem ACL inherited from the parent directory.
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&path)
                .map_err(|e| KeystoreError::Io(format!("stat: {e}")))?
                .permissions();
            perms.set_mode(0o600);
            fs::set_permissions(&path, perms)
                .map_err(|e| KeystoreError::Io(format!("chmod: {e}")))?;
        }

        Ok(())
    }

    fn load(&self, id: &KeystoreId) -> Result<DaemonIdentityMaterial, KeystoreError> {
        let path = self.path_for(id);
        let bytes = match fs::read(&path) {
            Ok(b) => b,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                return Err(KeystoreError::NotEnrolled);
            }
            Err(e) => return Err(KeystoreError::Io(e.to_string())),
        };
        if bytes.len() < SALT_LEN + NONCE_LEN + 16 {
            return Err(KeystoreError::Malformed("file too short".into()));
        }
        let salt = &bytes[..SALT_LEN];
        let nonce = &bytes[SALT_LEN..SALT_LEN + NONCE_LEN];
        let ciphertext = &bytes[SALT_LEN + NONCE_LEN..];

        let key = self.derive_key(salt)?;
        let cipher = ChaCha20Poly1305::new(Key::from_slice(key.as_slice()));
        let plaintext = cipher
            .decrypt(Nonce::from_slice(nonce), ciphertext)
            .map_err(|_| KeystoreError::DecryptionFailed)?;
        Self::decode_plaintext(&plaintext)
    }

    fn erase(&self, id: &KeystoreId) -> Result<(), KeystoreError> {
        let path = self.path_for(id);
        match fs::metadata(&path) {
            Ok(meta) => {
                // Overwrite with zeros before unlink. Best-effort; on
                // CoW filesystems this does not guarantee physical
                // erasure, only a logical scrub.
                let zeros = vec![0u8; meta.len() as usize];
                fs::write(&path, &zeros).ok();
                fs::remove_file(&path).map_err(|e| KeystoreError::Io(e.to_string()))?;
                Ok(())
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(KeystoreError::Io(e.to_string())),
        }
    }

    fn backend_name(&self) -> &'static str {
        "encrypted-file"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn fresh_keystore() -> (TempDir, EncryptedFileKeystore) {
        let dir = TempDir::new().expect("tempdir");
        let secret: Zeroizing<Vec<u8>> = Zeroizing::new(b"host-master-secret".to_vec());
        let ks = EncryptedFileKeystore::new(dir.path().to_path_buf(), secret);
        (dir, ks)
    }

    #[test]
    fn round_trip_succeeds() {
        let (_dir, ks) = fresh_keystore();
        let id = KeystoreId::default();
        let original = DaemonIdentityMaterial::new(b"-CERT-".to_vec(), b"-KEY-".to_vec());
        ks.store(&id, &original).expect("store");
        let loaded = ks.load(&id).expect("load");
        assert_eq!(loaded.cert_chain_pem.as_slice(), b"-CERT-");
        assert_eq!(loaded.private_key_pem.as_slice(), b"-KEY-");
    }

    #[test]
    fn missing_returns_not_enrolled() {
        let (_dir, ks) = fresh_keystore();
        let result = ks.load(&KeystoreId::default());
        assert!(matches!(result, Err(KeystoreError::NotEnrolled)));
    }

    #[test]
    fn wrong_secret_fails_decryption() {
        let dir = TempDir::new().expect("tempdir");
        let id = KeystoreId::default();
        let identity = DaemonIdentityMaterial::new(b"cert".to_vec(), b"key".to_vec());

        let good: Zeroizing<Vec<u8>> = Zeroizing::new(b"good".to_vec());
        let ks_good = EncryptedFileKeystore::new(dir.path().to_path_buf(), good);
        ks_good.store(&id, &identity).expect("store");

        let bad: Zeroizing<Vec<u8>> = Zeroizing::new(b"bad".to_vec());
        let ks_bad = EncryptedFileKeystore::new(dir.path().to_path_buf(), bad);
        assert!(matches!(
            ks_bad.load(&id),
            Err(KeystoreError::DecryptionFailed)
        ));
    }

    #[test]
    fn tampered_file_fails_decryption() {
        let (dir, ks) = fresh_keystore();
        let id = KeystoreId::default();
        let identity = DaemonIdentityMaterial::new(b"cert".to_vec(), b"key".to_vec());
        ks.store(&id, &identity).expect("store");

        let path = dir.path().join(format!("{}.identity", id.0));
        let mut bytes = fs::read(&path).expect("read");
        let last = bytes.len() - 1;
        bytes[last] ^= 0xFF;
        fs::write(&path, &bytes).expect("rewrite");

        assert!(matches!(ks.load(&id), Err(KeystoreError::DecryptionFailed)));
    }

    #[test]
    fn erase_removes_file() {
        let (dir, ks) = fresh_keystore();
        let id = KeystoreId::default();
        let identity = DaemonIdentityMaterial::new(b"cert".to_vec(), b"key".to_vec());
        ks.store(&id, &identity).expect("store");
        ks.erase(&id).expect("erase");
        let path = dir.path().join(format!("{}.identity", id.0));
        assert!(!path.exists());
    }

    #[test]
    fn erase_missing_is_idempotent() {
        let (_dir, ks) = fresh_keystore();
        ks.erase(&KeystoreId::default()).expect("erase missing");
    }

    #[test]
    fn backend_name_reports_file() {
        let (_dir, ks) = fresh_keystore();
        assert_eq!(ks.backend_name(), "encrypted-file");
    }
}
