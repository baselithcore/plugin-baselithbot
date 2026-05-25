//! Offline telemetry spool backed by SQLite.
//!
//! When the gRPC stream is unavailable — connect failure, server
//! disconnect, transient network drop — outbound `AgentMessage`s are
//! serialized via prost and persisted to a single-table SQLite file.
//! On the next successful connect the runtime drains the spool back
//! onto the new stream in insertion order before resuming live
//! traffic, preserving causality of telemetry events emitted across
//! the outage.
//!
//! Bounds:
//!
//! * `max_rows` — hard cap on entry count. The oldest rows are
//!   evicted on insert when the table grows past this limit.
//! * `max_bytes` — hard cap on the sum of `byte_len`. Same eviction
//!   policy.
//!
//! Without these caps a multi-day outage on a chatty fleet could
//! exhaust local disk; with them the spool degrades gracefully into
//! a sliding window of the most recent N MB of telemetry.

use std::path::Path;
use std::time::SystemTime;

use baselith_redagent_proto as proto;
use parking_lot::Mutex;
use prost::Message;
use rusqlite::{params, Connection, OptionalExtension};
use thiserror::Error;
use tokio::sync::mpsc;
use tracing::{debug, info, warn};

/// Default cap on the number of rows held in the spool.
pub const DEFAULT_MAX_ROWS: usize = 50_000;
/// Default cap on the sum of payload bytes.
pub const DEFAULT_MAX_BYTES: u64 = 100 * 1024 * 1024;

/// Failures the spool surfaces.
#[derive(Debug, Error)]
pub enum SpoolError {
    #[error("sqlite error: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("prost encode/decode error: {0}")]
    Prost(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
}

/// SQLite-backed FIFO spool for outbound `AgentMessage`s.
pub struct Spool {
    conn: Mutex<Connection>,
    max_rows: usize,
    max_bytes: u64,
}

impl Spool {
    /// Open the spool at `path`, creating the schema on first use.
    pub fn open(path: &Path, max_rows: usize, max_bytes: u64) -> Result<Self, SpoolError> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let conn = Connection::open(path)?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.pragma_update(None, "synchronous", "NORMAL")?;
        conn.execute(
            "CREATE TABLE IF NOT EXISTS spool (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                inserted_at INTEGER NOT NULL,\
                payload BLOB NOT NULL,\
                byte_len INTEGER NOT NULL\
            )",
            [],
        )?;
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_spool_inserted_at ON spool(inserted_at)",
            [],
        )?;
        Ok(Self {
            conn: Mutex::new(conn),
            max_rows,
            max_bytes,
        })
    }

    /// Append a single message. Old rows are evicted to honor the
    /// configured caps after every insert.
    pub fn append(&self, msg: &proto::AgentMessage) -> Result<(), SpoolError> {
        let mut bytes = Vec::with_capacity(msg.encoded_len());
        msg.encode(&mut bytes)
            .map_err(|e| SpoolError::Prost(e.to_string()))?;
        let len = bytes.len() as i64;
        let now = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or_default();
        let conn = self.conn.lock();
        conn.execute(
            "INSERT INTO spool (inserted_at, payload, byte_len) VALUES (?1, ?2, ?3)",
            params![now, bytes, len],
        )?;
        evict_excess(&conn, self.max_rows, self.max_bytes)?;
        Ok(())
    }

    /// Drain spooled messages onto `tx` in id order. Stops at the
    /// first `tx.send` failure (channel closed) and leaves the
    /// remaining rows on disk for the next session.
    pub async fn drain_to(
        &self,
        tx: &mpsc::Sender<proto::AgentMessage>,
    ) -> Result<usize, SpoolError> {
        let mut sent = 0usize;
        loop {
            let row: Option<(i64, Vec<u8>)> = {
                let conn = self.conn.lock();
                conn.query_row(
                    "SELECT id, payload FROM spool ORDER BY id LIMIT 1",
                    [],
                    |r| Ok((r.get::<_, i64>(0)?, r.get::<_, Vec<u8>>(1)?)),
                )
                .optional()?
            };
            let Some((id, bytes)) = row else { break };
            let msg = proto::AgentMessage::decode(bytes.as_slice())
                .map_err(|e| SpoolError::Prost(e.to_string()))?;
            if tx.send(msg).await.is_err() {
                debug!("spool drain interrupted: outbound channel closed");
                break;
            }
            let conn = self.conn.lock();
            conn.execute("DELETE FROM spool WHERE id = ?1", params![id])?;
            sent += 1;
        }
        if sent > 0 {
            info!(sent, "drained offline spool onto live stream");
        }
        Ok(sent)
    }

    /// Current row count. Used by health probes and tests.
    #[allow(dead_code)]
    pub fn len(&self) -> Result<usize, SpoolError> {
        let conn = self.conn.lock();
        let n: i64 = conn.query_row("SELECT COUNT(*) FROM spool", [], |r| r.get(0))?;
        Ok(n as usize)
    }

    /// True when no messages are queued.
    #[allow(dead_code)]
    pub fn is_empty(&self) -> Result<bool, SpoolError> {
        Ok(self.len()? == 0)
    }
}

fn evict_excess(conn: &Connection, max_rows: usize, max_bytes: u64) -> Result<(), rusqlite::Error> {
    // Row-count cap.
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM spool", [], |r| r.get(0))?;
    if count as usize > max_rows {
        let evict = count as usize - max_rows;
        conn.execute(
            "DELETE FROM spool WHERE id IN (SELECT id FROM spool ORDER BY id LIMIT ?1)",
            params![evict as i64],
        )?;
    }
    // Byte-sum cap. Evict the oldest rows in batches until under cap.
    loop {
        let total: i64 =
            conn.query_row("SELECT COALESCE(SUM(byte_len), 0) FROM spool", [], |r| {
                r.get(0)
            })?;
        if (total as u64) <= max_bytes {
            break;
        }
        let dropped = conn.execute(
            "DELETE FROM spool WHERE id IN (SELECT id FROM spool ORDER BY id LIMIT 64)",
            [],
        )?;
        if dropped == 0 {
            warn!(
                total,
                max_bytes, "spool over byte cap but cannot evict further"
            );
            break;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp() -> std::path::PathBuf {
        std::env::temp_dir().join(format!("baselith-spool-{}.sqlite", uuid::Uuid::new_v4()))
    }

    fn dummy(seq: u64) -> proto::AgentMessage {
        proto::AgentMessage {
            seq,
            nonce: vec![0u8; 16],
            ts: None,
            payload: Some(proto::v1::agent_message::Payload::Heartbeat(
                proto::Heartbeat::default(),
            )),
        }
    }

    #[test]
    fn append_and_count() {
        let path = tmp();
        let spool = Spool::open(&path, 100, 1_000_000).unwrap();
        spool.append(&dummy(1)).unwrap();
        spool.append(&dummy(2)).unwrap();
        assert_eq!(spool.len().unwrap(), 2);
        let _ = std::fs::remove_file(path);
    }

    #[tokio::test]
    async fn drain_preserves_order() {
        let path = tmp();
        let spool = Spool::open(&path, 100, 1_000_000).unwrap();
        for i in 1..=5 {
            spool.append(&dummy(i)).unwrap();
        }
        let (tx, mut rx) = mpsc::channel(8);
        let sent = spool.drain_to(&tx).await.unwrap();
        assert_eq!(sent, 5);
        assert_eq!(spool.len().unwrap(), 0);
        for i in 1..=5 {
            let msg = rx.recv().await.unwrap();
            assert_eq!(msg.seq, i);
        }
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn row_cap_evicts_oldest() {
        let path = tmp();
        let spool = Spool::open(&path, 3, 1_000_000).unwrap();
        for i in 1..=5 {
            spool.append(&dummy(i)).unwrap();
        }
        assert_eq!(spool.len().unwrap(), 3);
        let _ = std::fs::remove_file(path);
    }

    #[test]
    fn byte_cap_evicts() {
        let path = tmp();
        // Force tight byte cap so a couple of dummy heartbeats trip it.
        let spool = Spool::open(&path, 100, 32).unwrap();
        for i in 1..=10 {
            spool.append(&dummy(i)).unwrap();
        }
        assert!(spool.len().unwrap() < 10);
        let _ = std::fs::remove_file(path);
    }
}
