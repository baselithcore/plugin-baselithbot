# Runbook — Deploy server DGX Spark (single-tenant)

Procedura per deploy doCheck su server NVIDIA DGX Spark dedicato, single-tenant, on-prem.

**Audience**: ops / SRE.
**Frequenza**: una tantum per ambiente. Aggiornamento via re-deploy.
**Rollback time obiettivo**: ≤ 15 min.

## Prerequisiti

- Host NVIDIA DGX Spark, Ubuntu 22.04 LTS, kernel ≥ 5.15.
- Driver NVIDIA + CUDA 12.x installati. `nvidia-smi` mostra GPU.
- Docker 24+ + Docker Compose plugin v2.x.
- NVIDIA Container Toolkit (`nvidia-ctk runtime configure`).
- Volumi cifrati LUKS per `storage/`, `models/`, `audit-backup/`.
- Connettività rete: solo verso registry interno + repo Git (NO internet generale).

## Layout filesystem (raccomandato)

```
/opt/docheck/
├── repo/                          # git checkout
│   └── docker/compose.yml
├── storage/                       # mounted volume LUKS
│   ├── docs/                      # documenti caricati (sha256)
│   ├── chroma/                    # vector index
│   ├── docheck.db                 # SQLite cifrato (SQLCipher)
│   └── audit_ed25519.key          # 0600, in keychain post-GA
├── models/                        # weights vLLM
│   └── llama-3.3-70b-instruct-q4_k_m/
└── env/
    └── docheck.env                # production env vars (chmod 0600)
```

## 1. Preparazione modelli

Air-gapped: copia pesi da fonte trusted (USB cifrata, share interna).

```bash
sudo mkdir -p /opt/docheck/models
sudo chown -R docheck:docheck /opt/docheck/models
# Trasferisci weights:
rsync -av --progress source:/path/to/weights/ /opt/docheck/models/
```

Verifica checksum vs manifesto fornitore.

## 2. Setup volumi cifrati

```bash
# Crea container LUKS
sudo cryptsetup luksFormat /dev/nvme0n1p2
sudo cryptsetup open /dev/nvme0n1p2 docheck-storage
sudo mkfs.ext4 /dev/mapper/docheck-storage

# Mount
sudo mkdir -p /opt/docheck/storage
sudo mount /dev/mapper/docheck-storage /opt/docheck/storage

# Auto-unlock al boot via /etc/crypttab + keyfile su volume root cifrato
```

## 3. Env file

`/opt/docheck/env/docheck.env`:

```dotenv
DOCHECK_DEBUG=false
DOCHECK_STORAGE_ROOT=/data/storage
DOCHECK_DB_PATH=/data/storage/docheck.db
DOCHECK_SOCKET_PATH=/data/storage/docheck.sock

# DB encryption
DOCHECK_DB_ENCRYPTION_ENABLED=true
DOCHECK_DB_KEY_KEYRING_SERVICE=docheck
DOCHECK_DB_KEY_KEYRING_USER=master

# LLM via vLLM container interno
DOCHECK_LLM_PROVIDER=vllm
DOCHECK_LLM_BASE_URL=http://vllm:8000/v1
DOCHECK_LLM_PRIMARY_MODEL=llama-3.3-70b-instruct-q4_k_m
DOCHECK_LLM_FALLBACK_MODEL=llama-3.1-8b-instruct
DOCHECK_LLM_REQUEST_TIMEOUT_S=180

DOCHECK_EMBEDDING_MODEL=BAAI/bge-m3
DOCHECK_VECTOR_BACKEND=chroma
DOCHECK_CHROMA_PERSIST_DIR=/data/storage/chroma
DOCHECK_OCR_ENGINE=paddleocr

DOCHECK_RETENTION_DEFAULT_DAYS=365
```

Permission: `chmod 0600 /opt/docheck/env/docheck.env; chown docheck:docheck`.

## 4. Pull immagini

Da registry interno:

```bash
docker pull registry.internal/docheck/engine:0.1.0
docker pull registry.internal/docheck/vllm:0.6.x
docker pull registry.internal/docheck/ui-static:0.1.0
```

## 5. Avvio stack

```bash
cd /opt/docheck/repo
docker compose -f docker/compose.yml --env-file /opt/docheck/env/docheck.env up -d
docker compose ps
docker compose logs -f engine
```

Attendi log `docheck.startup version=0.1.0`. vLLM startup (load weights) richiede ~3-5 min su DGX.

## 6. Smoke test

```bash
# Health (via Unix socket dentro container o porta esposta)
curl --unix-socket /opt/docheck/storage/docheck.sock http://localhost/api/v1/health

# LLM probe
curl --unix-socket /opt/docheck/storage/docheck.sock \
  -X POST http://localhost/api/v1/system/llm/probe \
  -H "Authorization: Bearer <admin-jwt>"
```

Atteso: `{"status":"ok","latency_ms":<n>,"model":"llama-3.3-70b-instruct-q4_k_m"}`.

## 7. Egress validation

```bash
# Container engine deve avere zero traffico verso non-loopback / non-internal
docker exec docheck-engine sh -c 'apt-get install -y tcpdump && tcpdump -i eth0 -c 100 "not (dst net 127.0.0.0/8 or dst net 172.16.0.0/12)"'
# Atteso: timeout o 0 packets durante operazioni normali
```

Esegui con un'analisi documento in corso. Se vedi pacchetti uscenti → ferma stack, indaga, **non rilasciare in produzione**.

## 8. Backup setup

Cron job giornaliero su nodo bastion:

```bash
0 2 * * * /opt/docheck/scripts/backup.sh
```

`backup.sh` (snapshot atomic):

```bash
#!/usr/bin/env bash
set -euo pipefail
DEST=/mnt/backup/docheck/$(date +%Y%m%d)
mkdir -p "$DEST"
docker compose -f /opt/docheck/repo/docker/compose.yml exec -T engine \
  sqlite3 /data/storage/docheck.db ".backup '/data/storage/backup.db'"
cp /opt/docheck/storage/backup.db "$DEST/docheck.db"
tar -czf "$DEST/chroma.tar.gz" -C /opt/docheck/storage chroma/
gpg --encrypt --recipient ops@example.invalid -o "$DEST/audit_key.gpg" /opt/docheck/storage/audit_ed25519.key
```

Audit key cifrata con GPG ops team. Ritention 30 giorni rolling + 1 snapshot mensile permanente.

## 9. Monitoring

- Logs: `docker compose logs` → forward via filebeat/promtail al SIEM interno.
- Metrics: `GET /api/v1/system/cache`, `/system/storage`, `/system/runtime` polled da Prometheus laterale.
- Alert: chain integrity fail (`/audit/verify` → `ok=false`), latency LLM > 5s, disk usage > 80%.

## 10. Rollback

```bash
# Stop stack corrente
docker compose -f docker/compose.yml down

# Restore DB backup precedente
cp /mnt/backup/docheck/<YYYYMMDD>/docheck.db /opt/docheck/storage/docheck.db

# Restore vector index
tar -xzf /mnt/backup/docheck/<YYYYMMDD>/chroma.tar.gz -C /opt/docheck/storage/

# Re-pull immagine versione precedente
docker pull registry.internal/docheck/engine:<previous-version>
# Edit compose.yml o usa tag override

# Re-up
docker compose -f docker/compose.yml up -d
```

Verifica chain post-rollback: `GET /api/v1/audit/verify` → `ok=true`. Se `ok=false`, vedi [restore-audit.md](restore-audit.md).

## Troubleshooting

| Sintomo | Causa probabile | Fix |
|---------|-----------------|-----|
| `engine` container restart loop | DB migration fail | `docker logs docheck-engine` → check Alembic error; restore backup |
| vLLM OOM | weights troppo grandi vs VRAM | Q4_K_M obbligatorio su Spark; verifica `nvidia-smi` |
| Chain `verify` fail | tampering / corruzione DB | [restore-audit.md](restore-audit.md) |
| Egress packet detected | misconfig NetworkPolicy | block via iptables emergency; investiga |
| Disco pieno `storage/docs` | retention non purga | esegui purge manuale via `POST /system/retention` PUT a 30gg, attendi job |

## Checklist post-deploy

- [ ] Health endpoint `200 ok`.
- [ ] LLM probe `<3s` latency primo token.
- [ ] Audit verify `ok=true`.
- [ ] Smoke test analisi documento sample → finding glass-box.
- [ ] Egress tcpdump validation `0 packets`.
- [ ] Backup cron schedulato + primo run successful.
- [ ] Monitoring/alerting configurato.
- [ ] Documentazione versione deployata aggiornata.

## Vedi anche

- [setup-dev.md](setup-dev.md) — ambiente sviluppo.
- [rotate-keys.md](rotate-keys.md) — rotation chiave audit/JWT.
- [restore-audit.md](restore-audit.md) — recovery audit chain.
- [explanation/security-model.md](../explanation/security-model.md) — controlli sicurezza.
