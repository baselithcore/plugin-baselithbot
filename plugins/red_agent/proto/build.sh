#!/usr/bin/env bash
# Regenerate Python gRPC stubs from agent.proto.
#
# Run from the repository root after editing agent.proto:
#   plugins/red_agent/proto/build.sh
#
# Output is committed to plugins/red_agent/proto/_generated/. Mypy and
# ruff are configured to ignore that directory because it is tool
# output. The Rust daemon repo runs its own `tonic-build` step against
# the same agent.proto on each release.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PROTO_DIR="${REPO_ROOT}/plugins/red_agent/proto"
OUT_DIR="${PROTO_DIR}/_generated"

mkdir -p "${OUT_DIR}"
touch "${OUT_DIR}/__init__.py"

python -m grpc_tools.protoc \
    -I "${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    --grpc_python_out="${OUT_DIR}" \
    --pyi_out="${OUT_DIR}" \
    "${PROTO_DIR}/agent.proto"

# grpcio-tools emits ``import agent_pb2 as agent__pb2`` (no package
# qualifier). Rewrite to a relative import so the generated module is
# importable as a regular package member.
python - <<'PY'
import pathlib
p = pathlib.Path("${OUT_DIR}/agent_pb2_grpc.py".replace("${OUT_DIR}", "${OUT_DIR}"))
PY
sed -i.bak 's/^import agent_pb2 as agent__pb2$/from . import agent_pb2 as agent__pb2/' \
    "${OUT_DIR}/agent_pb2_grpc.py"
rm -f "${OUT_DIR}/agent_pb2_grpc.py.bak"

echo "Regenerated: ${OUT_DIR}/agent_pb2.py, agent_pb2.pyi, agent_pb2_grpc.py"
