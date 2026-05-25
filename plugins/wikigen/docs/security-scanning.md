# Security Scanning & SBOM

Pipeline scanner integrati in CI + script locale. Tutti i report finiscono in artefatti scaricabili (30-90 giorni retention).

## Tooling

|Scanner|Cosa|Where|
|-------|----|-----|
|`pip-audit`|Python deps CVE (PyPI Advisory DB + OSV)|GH/GitLab CI + local|
|`bandit`|Python static security analysis (SQLi, hardcoded secrets, weak crypto)|GH/GitLab CI + local|
|`npm audit`|Node deps CVE (npm registry advisories)|GH/GitLab CI + local|
|`cyclonedx-py`|SBOM Python (CycloneDX 1.5 JSON)|GH/GitLab CI + local|
|`cyclonedx-npm`|SBOM Node (CycloneDX 1.5 JSON)|GH/GitLab CI + local|
|`trivy fs`|Filesystem secrets + Dockerfile/IaC misconfig + deps CVE|GH/GitLab CI + local|
|`trivy image`|Container image OS + lib CVE|GH (post-build) + GitLab (protected)|

## Local run

```bash
# Tutto in un colpo
./scripts/security_scan.sh

# Con scan immagine
TRIVY_IMAGE=llm-wiki:latest ./scripts/security_scan.sh

# Output -> reports/security/
```

Pre-requisiti opzionali:

```bash
pip install "bandit[toml]" pip-audit "cyclonedx-bom>=4.0"
npm install -g @cyclonedx/cyclonedx-npm
brew install trivy   # o https://aquasecurity.github.io/trivy/
```

## CI integration

### GitHub Actions

Job `security` in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — gira pip-audit + bandit + SBOM + Trivy fs su ogni PR/push. Trivy SARIF auto-uploadato a GitHub Security tab. Job `docker-build` esegue Trivy image post-build.

Artifact: `security-reports` (30 giorni).

### GitLab CI

Stage `security` in [`.gitlab-ci.yml`](../.gitlab-ci.yml) — job paralleli:

- `pip_audit`, `bandit`, `npm_audit`, `sbom`, `trivy_fs` su ogni pipeline
- `trivy_image` solo su default branch / tag (richiede DinD + immagine pubblicata)

Tutti gli artefatti scaricabili dalla Pipeline UI; SBOM tenuto 90gg.

## Bandit config

Vedi `[tool.bandit]` in [`pyproject.toml`](../pyproject.toml). Skip: `B101` (assert in test/invariant guard), `B404`/`B603` (subprocess controllati nello scaffold).

## SBOM uso

Spec: CycloneDX 1.5 JSON. Compatibile con:

- Dependency Track ([`OWASP Dependency Track`](https://dependencytrack.org/)) — ingest periodico per tracking continuo CVE post-deploy.
- `grype sbom:./reports/security/sbom-python.json` — re-scan offline contro DB recente.

Pubblica SBOM con la release per audit cliente (ISO 27001 A.8.8 vulnerability mgmt).

## Triage workflow

1. Pipeline rossa per `HIGH/CRITICAL` non ignorati → review job log artefatto.
2. False positive → `# nosec` inline (bandit) o `--ignore-vuln` (pip-audit) con commento + link issue.
3. CVE upstream non patched → registra in [`SECURITY.md`](../SECURITY.md) (TODO se non esiste) con mitigation + ETA.
4. Container CVE in OS package → rebuild immagine settimanale (CI cron) basta nella maggioranza dei casi.

## Baseline findings (triage completato 2026-05-02)

Run su `llm_wiki/` (17905 LOC). Tutti i HIGH/MEDIUM finding triagiati come false positive e marcati con `# nosec` + motivazione inline:

|Severity|Issue|Files|Outcome|
|--------|-----|-----|-------|
|HIGH (1)|`B701` Jinja2 autoescape=False|`admin/prompt_synthesizer.py:309`|False positive — Environment usato per generare prompt LLM (testo server-side, mai HTML browser). Autoescape romperebbe `<DOMINIO>` in `&lt;DOMINIO&gt;`. `# nosec B701`|
|MEDIUM (6)|`B608` SQL f-string construction|`db/{conversations,feedback,memories,tenants,users}.py`|False positive — `where`/`updates` sono whitelist locali di clausole `"col = %s"`; nessun input utente concatenato; valori bound via `params` tuple a psycopg. `# nosec B608` con commento|

Stato attuale: HIGH=0, MEDIUM=0, LOW=14 (ratchet). CI `bandit` è **blocking su HIGH+MEDIUM** (`-ll`), LOW non blocca.

## Schedule consigliato

- Per push/PR: tutti gli scanner (auto via CI)
- Settimanale: rebuild container + Trivy image scan + SBOM pubblicato (cron CI)
- Trimestrale: pen-test esterno + dependency-track sync DB
- Annuale: full audit + SOC2/ISO compliance review
