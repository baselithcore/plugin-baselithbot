# Load Testing & Capacity Baseline

Profili k6 per misurare SLO e dimensionare hardware. Due scenari indipendenti perché LLM streaming e read-heavy traffic hanno colli di bottiglia diversi.

## Scenari

|Scenario|File|Obiettivo|Concorrenza tipica|
|--------|----|---------|------------------|
|`baseline`|[`k6_baseline.js`](../tests/loadtest/k6_baseline.js)|API auth + read (no LLM). Stress reale FastAPI + Postgres + Qdrant retrieval|50 VU per 2m steady|
|`chat_stream`|[`k6_chat_stream.js`](../tests/loadtest/k6_chat_stream.js)|Endpoint NDJSON streaming `/api/chat/stream`. Misura TTFT + token rate|4-8 VU (LLM-bound)|

## Run locale

```bash
# Install k6
brew install k6        # mac
# o: curl -fsSL https://dl.k6.io/key.gpg | sudo apt-key add -

# Baseline
k6 run -e BASE_URL=http://localhost:8000 \
       -e LOGIN_EMAIL=admin@example.com -e LOGIN_PASSWORD=*** \
       tests/loadtest/k6_baseline.js

# Chat streaming
k6 run -e BASE_URL=http://localhost:8000 \
       -e BEARER=eyJhbGc... \
       -e VUS=4 \
       tests/loadtest/k6_chat_stream.js
```

## Run via CI (GitHub)

Workflow [`loadtest.yml`](../.github/workflows/loadtest.yml) — manual dispatch.

```text
Actions -> Load test -> Run workflow
  scenario: baseline | chat_stream
  base_url: https://staging.wiki.example.com
```

Secrets richiesti: `LOADTEST_LOGIN_EMAIL`, `LOADTEST_LOGIN_PASSWORD`, `LOADTEST_BEARER`.

## SLO baseline

Soglie hard-codate in `options.thresholds`:

|Metric|p95|p99|Razionale|
|------|---|---|---------|
|Health endpoints|<100ms|<300ms|deve essere quasi gratis|
|Read API (groups, index, page)|<500ms|<1500ms|include vector search Qdrant|
|Auth (login/refresh)|<800ms|<2000ms|bcrypt + DB write|
|Error rate|<1%|—|tutti gli endpoint|
|Chat TTFT (primo token)|<5s|—|LLM-bound; dipende da modello|
|Chat total (60 token medio)|<60s|—|cap conservativo|

Run con thresholds violati → exit 1 → CI rosso.

## Capacity planning

### Single-host (8 vCPU, 16GB RAM, no GPU)

|Risorsa|Capacità misurata|Note|
|-------|-----------------|----|
|HTTP API read|~150 RPS sustained|FastAPI 1 worker; con `gunicorn -w 4` arriva a ~600 RPS|
|Postgres connections|pool 20|`POSTGRES_POOL_MAX`; alza a 50 con >2 worker|
|Qdrant retrieval|~100 query/s|BGE-M3 dense+sparse hybrid, top-50→rerank top-10|
|Chat concurrent users|2-4|Ollama serializza (CPU); con GPU ~10-15|
|Ingest workers|1|`INGEST_MAX_CONCURRENT=1` default; oltre intasa Ollama|

> Numeri indicativi da raccogliere su staging — popolare questa tabella dopo prima campagna.

### Bottleneck mapping

|Bottleneck osservato|Sintomo|Mitigation|
|--------------------|-------|----------|
|FastAPI single worker CPU-bound|p95 read >500ms con <50 RPS|`gunicorn -w $(nproc)` worker class uvicorn|
|Postgres pool exhausted|`PoolTimeout` in log|Alza `POSTGRES_POOL_MAX`; verifica long-running query|
|Qdrant payload index missing|search >100ms su collection grandi|crea payload index su `tenant_id`/`user_id`|
|Ollama queue|TTFT > 10s con >4 VU|GPU + `OLLAMA_NUM_PARALLEL=4`; oppure fan-out su 2 endpoint|
|Memory leak embedder|RSS cresce nel tempo|reload worker ogni N richieste (`--max-requests 1000`)|

## Cadenza

- Pre-release: baseline + chat_stream su staging, confronto contro baseline storico in `loadtest-summary.json`.
- Settimanale staging: solo `baseline` (per detect regressioni accidentali post-merge).
- Trimestrale: capacity review completa con dimensionamento aggiornato.

## Limitazioni note

- k6 non implementa true HTTP streaming — `k6_chat_stream.js` legge body completo e approssima TTFT al `tEnd`. Per TTFT preciso usa `xk6-streaming` build oppure misura lato server (OTel span su primo `yield` in `chat_stream`).
- Nessun `ingest` profile — preferire test singolo PDF + osservazione manuale OTel (lo stress di ingest è lato Ollama, non lato app).
