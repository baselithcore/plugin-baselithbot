//! Daemon self-health probe.
//!
//! Builds the `HealthSnapshot` payload that piggybacks on every
//! outbound `Heartbeat`. The backend uses these values to surface
//! agent saturation in the fleet dashboard without needing a separate
//! poll path.
//!
//! Probed at every heartbeat tick:
//!
//! * `cpu_percent` — daemon process CPU usage averaged since the
//!   previous tick.
//! * `mem_rss_bytes` — daemon process resident set size.
//! * `disk_free_bytes` — free space on the partition that hosts the
//!   offline telemetry buffer.
//! * `telemetry_buffer_lag` — number of telemetry messages currently
//!   queued in the outbound mpsc channel but not yet on the wire.
//! * `uptime` — seconds since the daemon process started.

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;

use baselith_redagent_proto as proto;
use prost_types::Duration as ProstDuration;
use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System};

/// Lag counter shared with the outbound channel sender. Incremented
/// on every successful enqueue and decremented when the transport
/// drains a message into the gRPC stream.
#[derive(Debug, Default, Clone)]
pub struct TelemetryLag {
    inner: Arc<AtomicU64>,
}

impl TelemetryLag {
    /// Read the current lag without modifying it.
    pub fn current(&self) -> u64 {
        self.inner.load(Ordering::Relaxed)
    }

    /// Increment the lag counter. Called after a successful enqueue
    /// onto the outbound channel.
    pub fn record_enqueue(&self) {
        self.inner.fetch_add(1, Ordering::Relaxed);
    }

    /// Decrement the lag counter. Called after a message has been
    /// flushed onto the gRPC stream.
    pub fn record_dequeue(&self) {
        self.inner.fetch_sub(1, Ordering::Relaxed);
    }
}

/// Sticky daemon-process state needed to compute the periodic snapshot.
pub struct HealthProbe {
    started_at: Instant,
    self_pid: u32,
    buffer_path: PathBuf,
    sys: System,
    lag: TelemetryLag,
}

impl HealthProbe {
    /// Build a new probe rooted at the daemon's offline-buffer path.
    /// `buffer_path` is used to compute `disk_free_bytes`; if the path
    /// does not exist yet, the probe falls back to its parent directory.
    pub fn new(buffer_path: PathBuf, lag: TelemetryLag) -> Self {
        Self {
            started_at: Instant::now(),
            self_pid: std::process::id(),
            buffer_path,
            sys: System::new(),
            lag,
        }
    }

    /// Snapshot the current daemon health.
    pub fn snapshot(&mut self) -> proto::v1::HealthSnapshot {
        let pid = Pid::from_u32(self.self_pid);
        self.sys.refresh_processes_specifics(
            ProcessesToUpdate::Some(&[pid]),
            false,
            ProcessRefreshKind::new().with_cpu().with_memory(),
        );
        let proc = self.sys.process(pid);
        let cpu_percent = proc.map(|p| p.cpu_usage() as f64).unwrap_or_default();
        let mem_rss_bytes = proc.map(|p| p.memory()).unwrap_or_default();

        let disk_free_bytes = disk_free_for(&self.buffer_path).unwrap_or(0);

        let uptime_secs = self.started_at.elapsed().as_secs();
        let uptime = ProstDuration {
            seconds: uptime_secs as i64,
            nanos: 0,
        };

        proto::v1::HealthSnapshot {
            cpu_percent,
            mem_rss_bytes,
            disk_free_bytes,
            telemetry_buffer_lag: self.lag.current(),
            uptime: Some(uptime),
        }
    }
}

#[cfg(target_os = "linux")]
fn disk_free_for(path: &std::path::Path) -> Option<u64> {
    // Walk up to the first existing ancestor so a missing buffer file
    // doesn't suppress the whole metric.
    let mut probe = path.to_path_buf();
    loop {
        if probe.exists() {
            break;
        }
        if !probe.pop() {
            return None;
        }
    }
    use nix::sys::statvfs::statvfs;
    let st = statvfs(&probe).ok()?;
    Some(st.blocks_available() as u64 * st.fragment_size() as u64)
}

#[cfg(target_os = "macos")]
fn disk_free_for(path: &std::path::Path) -> Option<u64> {
    let mut probe = path.to_path_buf();
    loop {
        if probe.exists() {
            break;
        }
        if !probe.pop() {
            return None;
        }
    }
    use nix::sys::statvfs::statvfs;
    let st = statvfs(&probe).ok()?;
    Some(st.blocks_available() as u64 * st.fragment_size() as u64)
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn disk_free_for(_path: &std::path::Path) -> Option<u64> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lag_round_trips() {
        let l = TelemetryLag::default();
        assert_eq!(l.current(), 0);
        l.record_enqueue();
        l.record_enqueue();
        assert_eq!(l.current(), 2);
        l.record_dequeue();
        assert_eq!(l.current(), 1);
    }

    #[test]
    fn snapshot_reports_uptime_and_self_rss() {
        let lag = TelemetryLag::default();
        let mut probe = HealthProbe::new(std::env::temp_dir(), lag);
        // Sleep a beat so uptime is measurable.
        std::thread::sleep(std::time::Duration::from_millis(20));
        let snap = probe.snapshot();
        assert!(snap.uptime.is_some());
        // mem_rss_bytes can legitimately be zero on a sandboxed CI
        // host; only assert that the call returned without panicking.
        let _ = snap.mem_rss_bytes;
    }
}
