//! On-demand file hashing.
//!
//! Used by the `HashFilesCmd` dispatcher to produce SHA-256 digests
//! for the policy-allowed paths the backend asked to attest.
//!
//! Streams the file in 64 KiB chunks so a multi-GB binary does not
//! materialize in memory. Each path returns a `FileDigest` with the
//! sha256 hex, file size, and any error captured per-path so a single
//! permission denial does not abort the whole batch.

use std::io::Read;
use std::path::{Path, PathBuf};

use serde::Serialize;
use sha2::{Digest, Sha256};

const READ_CHUNK: usize = 64 * 1024;
/// Hard cap to keep a single hash bounded in time. Files larger than
/// this return a `truncated: true` digest computed over the first
/// `MAX_FILE_BYTES` bytes — useful for log files where forensic value
/// is in the prefix.
pub const MAX_FILE_BYTES: u64 = 256 * 1024 * 1024;

/// Per-path hashing outcome.
#[derive(Debug, Clone, Serialize)]
pub struct FileDigest {
    /// Absolute path the digest applies to.
    pub path: String,
    /// SHA-256 in lowercase hex when present.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sha256: Option<String>,
    /// File size in bytes when readable.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub size_bytes: Option<u64>,
    /// True when the digest was computed over only the first
    /// `MAX_FILE_BYTES` bytes.
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    pub truncated: bool,
    /// Stable error code on failure (`PATH_DENIED`, `PATH_NOT_FOUND`,
    /// `IO_ERROR`).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_code: Option<String>,
    /// Human-readable error message.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// Hash a single absolute path. Never panics; all I/O failures are
/// folded into the returned `FileDigest`.
pub fn hash_file(path: &Path) -> FileDigest {
    let path_str = path.to_string_lossy().into_owned();

    let metadata = match std::fs::metadata(path) {
        Ok(m) => m,
        Err(e) => {
            let code = match e.kind() {
                std::io::ErrorKind::NotFound => "PATH_NOT_FOUND",
                std::io::ErrorKind::PermissionDenied => "PATH_DENIED",
                _ => "IO_ERROR",
            };
            return FileDigest {
                path: path_str,
                sha256: None,
                size_bytes: None,
                truncated: false,
                error_code: Some(code.to_string()),
                error: Some(e.to_string()),
            };
        }
    };
    if !metadata.is_file() {
        return FileDigest {
            path: path_str,
            sha256: None,
            size_bytes: Some(metadata.len()),
            truncated: false,
            error_code: Some("NOT_A_FILE".to_string()),
            error: Some("path is not a regular file".to_string()),
        };
    }

    let mut file = match std::fs::File::open(path) {
        Ok(f) => f,
        Err(e) => {
            return FileDigest {
                path: path_str,
                sha256: None,
                size_bytes: Some(metadata.len()),
                truncated: false,
                error_code: Some("IO_ERROR".to_string()),
                error: Some(e.to_string()),
            };
        }
    };

    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; READ_CHUNK];
    let mut consumed: u64 = 0;
    let mut truncated = false;
    loop {
        let take = ((MAX_FILE_BYTES - consumed) as usize).min(buf.len());
        if take == 0 {
            truncated = true;
            break;
        }
        match file.read(&mut buf[..take]) {
            Ok(0) => break,
            Ok(n) => {
                hasher.update(&buf[..n]);
                consumed += n as u64;
            }
            Err(e) => {
                return FileDigest {
                    path: path_str,
                    sha256: None,
                    size_bytes: Some(metadata.len()),
                    truncated: false,
                    error_code: Some("IO_ERROR".to_string()),
                    error: Some(e.to_string()),
                };
            }
        }
    }

    let digest = hasher.finalize();
    FileDigest {
        path: path_str,
        sha256: Some(hex::encode(digest)),
        size_bytes: Some(metadata.len()),
        truncated,
        error_code: None,
        error: None,
    }
}

/// Hash a batch of absolute paths. Order is preserved.
pub fn hash_files<I, P>(paths: I) -> Vec<FileDigest>
where
    I: IntoIterator<Item = P>,
    P: Into<PathBuf>,
{
    paths.into_iter().map(|p| hash_file(&p.into())).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn hashes_known_content() {
        let dir = tempdir();
        let path = dir.join("a.bin");
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(b"hello").unwrap();
        drop(f);

        let d = hash_file(&path);
        assert_eq!(d.size_bytes, Some(5));
        // sha256("hello")
        assert_eq!(
            d.sha256.unwrap(),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        );
        assert!(d.error_code.is_none());
    }

    #[test]
    fn missing_path_returns_not_found() {
        let d = hash_file(Path::new("/nonexistent/path/xyz"));
        assert_eq!(d.error_code.as_deref(), Some("PATH_NOT_FOUND"));
        assert!(d.sha256.is_none());
    }

    fn tempdir() -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!("baselith-hash-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&d).unwrap();
        d
    }
}
