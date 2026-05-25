//! Build script: regenerate tonic stubs from `../../../proto/agent.proto`.
//!
//! The proto file lives outside this crate (in the parent monorepo's
//! `plugins/red_agent/proto/agent.proto`). When the standalone daemon
//! repo is published via `git subtree split`, the proto directory is
//! mirrored alongside this workspace (`./proto/agent.proto`) so this
//! script must accept either layout.

use std::path::PathBuf;

fn main() {
    let proto = locate_proto();
    println!("cargo:rerun-if-changed={}", proto.display());

    // Server stubs are gated behind the `server` feature so the
    // production daemon binary stays client-only. Integration tests
    // (e.g. the mTLS handshake harness in `transport`) opt-in to
    // exercise the channel against a real in-process tonic server.
    let build_server = std::env::var("CARGO_FEATURE_SERVER").is_ok();

    // Include search path: the proto file's directory plus any
    // additional roots holding the well-known google/protobuf/*.proto
    // files. Distro `protobuf-compiler` packages drop them under
    // /usr/include or /usr/local/include; we add both unconditionally
    // and let protoc skip whichever doesn't exist on this host.
    let mut includes = vec![proto.parent().unwrap().to_path_buf()];
    for extra in [
        "/usr/include",
        "/usr/local/include",
        "/opt/homebrew/include",
    ] {
        if std::path::Path::new(extra).join("google/protobuf").exists() {
            includes.push(PathBuf::from(extra));
        }
    }

    tonic_build::configure()
        .build_server(build_server)
        .build_client(true)
        .out_dir(std::env::var("OUT_DIR").expect("OUT_DIR must be set"))
        .compile_protos(&[proto.as_path()], &includes)
        .expect("tonic compile failed for agent.proto");
}

fn locate_proto() -> PathBuf {
    // Order: monorepo path, then sibling (subtree-split) path.
    let candidates = [
        // In the monorepo: this crate is at
        // plugins/red_agent/daemon/crates/proto, and the proto file is
        // at plugins/red_agent/proto/agent.proto.
        PathBuf::from("../../../proto/agent.proto"),
        // In the standalone daemon repo: proto is mirrored at the
        // workspace root.
        PathBuf::from("../../proto/agent.proto"),
    ];
    for path in &candidates {
        if path.exists() {
            return path.clone();
        }
    }
    panic!(
        "agent.proto not found. Tried: {:?}",
        candidates
            .iter()
            .map(|p| p.display().to_string())
            .collect::<Vec<_>>()
    );
}
