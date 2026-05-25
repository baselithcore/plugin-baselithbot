#!/usr/bin/env bash
# CLAUDE.md §1.1 — hard 500 LOC limit per source file.
# Files annotated with `# noqa: file-loc` (anywhere in first 5 lines) are skipped.

set -euo pipefail

LIMIT=500

for f in "$@"; do
  [ -f "$f" ] || continue

  # Allow opt-out marker in the file header.
  if head -n 5 "$f" | grep -qE 'noqa:[[:space:]]*file-loc'; then
    continue
  fi

  loc=$(wc -l < "$f" | tr -d '[:space:]')
  if [ "$loc" -gt "$LIMIT" ]; then
    printf '\033[33m[warn] %s: %s LOC > %s (CLAUDE.md §1.1) — split into modules.\033[0m\n' \
      "$f" "$loc" "$LIMIT" >&2
  fi
done

# Non-blocking: warn only.
exit 0
