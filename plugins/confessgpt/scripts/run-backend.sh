#!/usr/bin/env bash
# ConfessGPT dev wrapper — boots the BaselithCore backend with the
# Vite dev origins added to the CSRF allowlist.
#
# Why: CSRF middleware reads ALLOW_ORIGINS from the root .env at
# startup. Plugin-local .env files load too late (during lifespan,
# after middleware is built). This wrapper injects the extra origins
# inline so the user's root .env stays untouched.
#
# Usage:
#   plugins/confessgpt/scripts/run-backend.sh
#
# Stop with Ctrl+C or `pkill -f "uvicorn backend:app"`.

set -euo pipefail

# Resolve repo root regardless of caller cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

cd "${REPO_ROOT}"

# Default base allowlist mirrors the values shipped in .env. Adding
# the Vite dev ports (5173, 5181, 4173) lets the React UI hit
# /api/confessgpt/* without tripping the CSRF Origin check.
export ALLOW_ORIGINS='[
  "http://localhost:8000",
  "http://127.0.0.1:8000",
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://localhost:5180",
  "http://127.0.0.1:5180",
  "http://localhost:5181",
  "http://127.0.0.1:5181",
  "http://localhost:5273",
  "http://127.0.0.1:5273",
  "http://localhost:4173",
  "http://127.0.0.1:4173"
]'

# Drop the embedded Qdrant lockfile only when no other Python proc
# already holds it — avoids racing the existing backend.
if [[ -f "${REPO_ROOT}/qdrant_data/.lock" ]]; then
  if ! lsof "${REPO_ROOT}/qdrant_data/.lock" >/dev/null 2>&1; then
    rm -f "${REPO_ROOT}/qdrant_data/.lock"
  fi
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "🌐 ConfessGPT backend → http://${HOST}:${PORT}"
echo "📜 Allowlist: localhost {5173,5180,5181,5273,4173,8000} (+ 127.0.0.1)"
echo

exec uvicorn backend:app --host "${HOST}" --port "${PORT}"
