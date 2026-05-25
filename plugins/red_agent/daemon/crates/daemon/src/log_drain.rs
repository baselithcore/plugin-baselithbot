//! Tracing → gRPC `LogBatch` bridge.
//!
//! Implements a `tracing_subscriber::Layer` that captures every
//! `WARN`+ event the daemon emits, packages it as a `proto::LogEntry`,
//! and pushes it onto a shared mpsc channel. A drain task batches up
//! to [`LOG_BATCH_SIZE`] entries (or flushes after [`LOG_FLUSH_MS`])
//! and emits a `LogBatch` envelope on the outbound `AgentMessage`
//! stream so operators can triage daemon-side issues from the same
//! UI as host telemetry.
//!
//! Trade-offs:
//!
//! * `WARN`+ only — `INFO`/`DEBUG` would dominate bandwidth on a
//!   chatty fleet. Operators that need verbose inspection should rely
//!   on the local stdout JSON sink.
//! * Bounded `mpsc(2048)` — if the drain falls behind the layer
//!   silently drops the surplus rather than blocking the producer
//!   (logging must never deadlock the daemon).

use std::time::Duration;

use baselith_redagent_proto as proto;
use tokio::sync::mpsc;
use tracing::field::{Field, Visit};
use tracing::Level;
use tracing_subscriber::layer::Context;
use tracing_subscriber::Layer;

use crate::wire::{now_timestamp, random_nonce};

/// Channel capacity for in-flight `LogEntry` items.
const LOG_CHANNEL_CAPACITY: usize = 2048;
/// Maximum entries packed into a single `LogBatch` envelope.
const LOG_BATCH_SIZE: usize = 64;
/// Flush cadence for partial batches, in milliseconds.
const LOG_FLUSH_MS: u64 = 2_000;

/// Sender half of the log-drain bridge. Cheap to clone (Arc inside).
#[derive(Clone)]
pub struct LogSink {
    tx: mpsc::Sender<proto::LogEntry>,
}

impl LogSink {
    fn enqueue(&self, entry: proto::LogEntry) {
        // Use try_send so a stalled drain never blocks a tracing call.
        let _ = self.tx.try_send(entry);
    }
}

/// Build a `Layer` + drain pair. The caller wires the layer into the
/// global subscriber and spawns the drain on the tokio runtime once
/// the outbound channel is available.
pub fn build() -> (LogLayer, LogDrain) {
    let (tx, rx) = mpsc::channel::<proto::LogEntry>(LOG_CHANNEL_CAPACITY);
    let sink = LogSink { tx };
    (LogLayer { sink: sink.clone() }, LogDrain { rx, sink })
}

/// Tracing-subscriber `Layer` that captures WARN+ events.
pub struct LogLayer {
    sink: LogSink,
}

impl<S> Layer<S> for LogLayer
where
    S: tracing::Subscriber,
{
    fn on_event(&self, event: &tracing::Event<'_>, _ctx: Context<'_, S>) {
        let metadata = event.metadata();
        let level = *metadata.level();
        if level > Level::WARN {
            // tracing levels: ERROR < WARN < INFO < DEBUG < TRACE in
            // the `Level` enum's PartialOrd. WARN is "less than" INFO.
            return;
        }
        let mut visitor = FieldVisitor::default();
        event.record(&mut visitor);
        let mut map = serde_json::Map::new();
        for (k, v) in visitor.fields {
            map.insert(k, v);
        }
        let entry = proto::LogEntry {
            ts: Some(now_timestamp()),
            level: level_to_proto(level) as i32,
            target: metadata.target().to_string(),
            message: visitor.message.unwrap_or_default(),
            fields: Some(baselith_redagent_collector::json_to_struct(
                serde_json::Value::Object(map),
            )),
            trace_id: String::new(),
        };
        self.sink.enqueue(entry);
    }
}

/// Drain side. Owned by exactly one task that forwards batches to the
/// outbound `AgentMessage` channel.
pub struct LogDrain {
    rx: mpsc::Receiver<proto::LogEntry>,
    sink: LogSink,
}

impl LogDrain {
    /// Run the drain loop. Returns when both the layer-side senders
    /// drop and the receiver closes (i.e. process shutdown).
    pub async fn run(mut self, outbound: mpsc::Sender<proto::AgentMessage>) {
        // Detach the dummy keep-alive sender so the drain exits when
        // every layer-side clone has been dropped.
        drop(self.sink);
        let mut buf: Vec<proto::LogEntry> = Vec::with_capacity(LOG_BATCH_SIZE);
        let mut interval = tokio::time::interval(Duration::from_millis(LOG_FLUSH_MS));
        let mut seq: u64 = 3_000_000;
        loop {
            tokio::select! {
                maybe = self.rx.recv() => {
                    match maybe {
                        Some(entry) => {
                            buf.push(entry);
                            if buf.len() >= LOG_BATCH_SIZE {
                                flush(&mut buf, &mut seq, &outbound).await;
                            }
                        }
                        None => {
                            flush(&mut buf, &mut seq, &outbound).await;
                            break;
                        }
                    }
                }
                _ = interval.tick() => {
                    if !buf.is_empty() {
                        flush(&mut buf, &mut seq, &outbound).await;
                    }
                }
            }
        }
    }
}

async fn flush(
    buf: &mut Vec<proto::LogEntry>,
    seq: &mut u64,
    outbound: &mpsc::Sender<proto::AgentMessage>,
) {
    if buf.is_empty() {
        return;
    }
    let entries = std::mem::take(buf);
    let msg = proto::AgentMessage {
        seq: *seq,
        nonce: random_nonce(),
        ts: Some(now_timestamp()),
        payload: Some(proto::v1::agent_message::Payload::Logs(
            proto::v1::LogBatch { entries },
        )),
    };
    let _ = outbound.send(msg).await;
    *seq = seq.wrapping_add(1);
}

fn level_to_proto(level: Level) -> proto::v1::LogLevel {
    use proto::v1::LogLevel;
    match level {
        Level::ERROR => LogLevel::Error,
        Level::WARN => LogLevel::Warn,
        Level::INFO => LogLevel::Info,
        Level::DEBUG => LogLevel::Debug,
        Level::TRACE => LogLevel::Trace,
    }
}

#[derive(Default)]
struct FieldVisitor {
    message: Option<String>,
    fields: Vec<(String, serde_json::Value)>,
}

impl Visit for FieldVisitor {
    fn record_str(&mut self, field: &Field, value: &str) {
        if field.name() == "message" {
            self.message = Some(value.to_string());
        } else {
            self.fields.push((
                field.name().to_string(),
                serde_json::Value::String(value.to_string()),
            ));
        }
    }

    fn record_bool(&mut self, field: &Field, value: bool) {
        self.fields
            .push((field.name().to_string(), serde_json::Value::Bool(value)));
    }

    fn record_i64(&mut self, field: &Field, value: i64) {
        self.fields.push((
            field.name().to_string(),
            serde_json::Value::Number(value.into()),
        ));
    }

    fn record_u64(&mut self, field: &Field, value: u64) {
        self.fields.push((
            field.name().to_string(),
            serde_json::Value::Number(value.into()),
        ));
    }

    fn record_f64(&mut self, field: &Field, value: f64) {
        let n = serde_json::Number::from_f64(value).unwrap_or_else(|| serde_json::Number::from(0));
        self.fields
            .push((field.name().to_string(), serde_json::Value::Number(n)));
    }

    fn record_debug(&mut self, field: &Field, value: &dyn std::fmt::Debug) {
        let s = format!("{value:?}");
        if field.name() == "message" {
            self.message = Some(s);
        } else {
            self.fields
                .push((field.name().to_string(), serde_json::Value::String(s)));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn level_mapping_round_trip() {
        assert_eq!(level_to_proto(Level::ERROR), proto::v1::LogLevel::Error);
        assert_eq!(level_to_proto(Level::WARN), proto::v1::LogLevel::Warn);
        assert_eq!(level_to_proto(Level::INFO), proto::v1::LogLevel::Info);
    }
}
