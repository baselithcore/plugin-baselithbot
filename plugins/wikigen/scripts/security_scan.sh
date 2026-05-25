#!/usr/bin/env bash
# =========================================================================
# security_scan.sh — security scan locale (pre-commit / pre-release)
#
# Esegue:
#   - bandit             (Python static security analysis)
#   - pip-audit          (Python deps CVE)
#   - npm audit          (Node deps CVE)
#   - cyclonedx-py       (SBOM Python -> sbom-python.json)
#   - cyclonedx-npm      (SBOM Node   -> sbom-node.json)
#   - trivy fs           (filesystem secrets + config misconfig) [se disponibile]
#   - trivy image        (container scan) [se TRIVY_IMAGE settato]
#
# Output: tutti i report finiscono in ./reports/security/
# Exit code: 1 se uno scanner trova HIGH/CRITICAL.
#
# Uso:
#   ./scripts/security_scan.sh
#   TRIVY_IMAGE=llm-wiki:latest ./scripts/security_scan.sh
# =========================================================================
set -uo pipefail

REPORTS_DIR="${REPORTS_DIR:-./reports/security}"
TRIVY_IMAGE="${TRIVY_IMAGE:-}"
FAIL=0

mkdir -p "$REPORTS_DIR"

run() {
    local name="$1"; shift
    echo "==[$name]=="
    if "$@"; then
        echo "[OK] $name"
    else
        local rc=$?
        echo "[WARN] $name exit=$rc"
        FAIL=1
    fi
    echo
}

# ----- Python static analysis -----
if command -v bandit >/dev/null 2>&1; then
    run "bandit" bandit -c pyproject.toml -r llm_wiki -f json -o "$REPORTS_DIR/bandit.json"
else
    echo "[skip] bandit non installato (pip install bandit[toml])"
fi

# ----- Python dependency CVEs -----
if command -v pip-audit >/dev/null 2>&1; then
    run "pip-audit" pip-audit --format json --output "$REPORTS_DIR/pip-audit.json"
else
    echo "[skip] pip-audit non installato (pip install pip-audit)"
fi

# ----- Node dependency CVEs -----
if [[ -d frontend ]] && command -v npm >/dev/null 2>&1; then
    (cd frontend && npm audit --audit-level=high --json > "../$REPORTS_DIR/npm-audit.json" 2>/dev/null) || FAIL=1
    echo "[OK] npm-audit -> $REPORTS_DIR/npm-audit.json"
fi

# ----- SBOM Python (CycloneDX) -----
if command -v cyclonedx-py >/dev/null 2>&1; then
    run "sbom-python" cyclonedx-py environment --output-format json --output-file "$REPORTS_DIR/sbom-python.json"
else
    echo "[skip] cyclonedx-py non installato (pip install cyclonedx-bom)"
fi

# ----- SBOM Node (CycloneDX) -----
if command -v cyclonedx-npm >/dev/null 2>&1 && [[ -d frontend ]]; then
    (cd frontend && cyclonedx-npm --output-format json --output-file "../$REPORTS_DIR/sbom-node.json") || FAIL=1
    echo "[OK] sbom-node -> $REPORTS_DIR/sbom-node.json"
else
    echo "[skip] cyclonedx-npm non installato (npm i -g @cyclonedx/cyclonedx-npm)"
fi

# ----- Trivy filesystem -----
if command -v trivy >/dev/null 2>&1; then
    run "trivy-fs" trivy fs --scanners vuln,secret,misconfig \
        --severity HIGH,CRITICAL \
        --format json --output "$REPORTS_DIR/trivy-fs.json" .

    if [[ -n "$TRIVY_IMAGE" ]]; then
        run "trivy-image" trivy image --severity HIGH,CRITICAL \
            --format json --output "$REPORTS_DIR/trivy-image.json" "$TRIVY_IMAGE"
    fi
else
    echo "[skip] trivy non installato (https://aquasecurity.github.io/trivy/)"
fi

echo
echo "=== Reports in $REPORTS_DIR ==="
ls -1 "$REPORTS_DIR" 2>/dev/null

if [[ $FAIL -eq 1 ]]; then
    echo "[FAIL] uno o più scanner ha trovato finding o ha errato"
    exit 1
fi
echo "[PASS] nessun finding HIGH/CRITICAL bloccante"
