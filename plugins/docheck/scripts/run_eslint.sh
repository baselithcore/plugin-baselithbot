#!/usr/bin/env bash
# Wrapper for ESLint v9: escape glob meta-chars (parens, brackets, braces, *, ?, !)
# in pre-commit-supplied filenames, since ESLint treats positional args as globby
# patterns and Next.js route groups like `(app)` are otherwise mis-interpreted.

set -euo pipefail

cd docheck-ui

files=()
for f in "$@"; do
  files+=("${f#docheck-ui/}")
done

[ "${#files[@]}" -eq 0 ] && exit 0

exec pnpm exec eslint --max-warnings=0 --no-warn-ignored "${files[@]}"
