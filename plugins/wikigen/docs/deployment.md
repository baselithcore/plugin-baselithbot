# Deployment

How-to per portare `wiki-white-label` da sviluppo a produzione. Per lo stack di osservabilità → [`observability.md`](observability.md). Per manutenzione corrente → [`operations.md`](operations.md).

## Topologie supportate

1. **Single-host** (default): tutto su una VM/bare-metal Linux. Adatto a deploy interni small-medium.
2. **Split DB**: Postgres + Qdrant gestiti (RDS / Aiven / Qdrant Cloud), app stateless replicabile.
3. **Multi-domain**: N processi `llm-wiki` (uno per `APP_DOMAIN`) dietro reverse proxy, condividendo Postgres + Qdrant.

> Multi-tenant per processo non è supportato: un processo = un `APP_DOMAIN`.

## 1. Single-host (riferimento)

### 1.1 Layout filesystem

```txt
/srv/llm-wiki/
├── app/                    # repo clonato
├── vaults/
│   ├── legal/
│   │   ├── wiki/
│   │   └── raw/
│   └── medical/
├── .env                    # secrets prod
├── logs/
└── backups/
    ├── postgres/
    └── qdrant/
```

### 1.2 Reverse proxy (Caddy esempio)

`/etc/caddy/Caddyfile`:

```caddy
wiki.example.com {
    encode zstd gzip

    # Frontend statico (build vite)
    handle_path /assets/* {
        root * /srv/llm-wiki/app/frontend/dist
        file_server
    }

    handle / {
        root * /srv/llm-wiki/app/frontend/dist
        try_files {path} /index.html
        file_server
    }

    # API + auth
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /auth/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /healthz {
        reverse_proxy 127.0.0.1:8000
    }

    # Header sicurezza aggiuntivi (l'app già aggiunge i propri)
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

Equivalente Nginx in repo (`deploy/nginx.conf` se presente; altrimenti adattabile dal Caddyfile).

### 1.3 Build frontend

```bash
cd frontend
npm ci
npm run build            # produce dist/
```

Servire `dist/` come statico (Caddy/Nginx). Variabile build:

```ini
# frontend/.env.production
VITE_API_BASE=https://wiki.example.com
```

### 1.4 systemd

`/etc/systemd/system/llm-wiki.service`:

```ini
[Unit]
Description=LLM Wiki API
After=network.target postgresql.service docker.service

[Service]
Type=exec
User=llm-wiki
Group=llm-wiki
WorkingDirectory=/srv/llm-wiki/app
EnvironmentFile=/srv/llm-wiki/.env
ExecStart=/srv/llm-wiki/app/.venv/bin/uvicorn main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --proxy-headers \
    --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/srv/llm-wiki/vaults /srv/llm-wiki/logs

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now llm-wiki
sudo journalctl -u llm-wiki -f
```

### 1.5 Workers

Workers consigliati: `min(2 * CPU_CORES, 4)`. Ogni worker:

- Carica embedder + reranker in RAM (~2GB ciascuno).
- Mantiene proprio pool psycopg.
- Esegue ingest jobs in-process (asyncio).

Per dataset grandi → considera **dedicated ingest worker**: un processo con `INGEST_*` configurato e `AUTO_INGEST_ON_STARTUP=true`, e un altro per servire chat senza ingest concorrente.

## 2. Docker Compose produzione

### 2.1 Compose principale

`docker-compose.yml` (root) include `qdrant`, `postgres`, `redis`, `falkordb`. Per produzione **non** esponi porte sull'host pubblico.

```yaml
# docker-compose.prod.yml (override)
services:
  qdrant:
    ports: !reset []          # bind solo network interno
    networks: [internal]

  postgres:
    ports: !reset []
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks: [internal]

  redis:
    ports: !reset []
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}"]
    networks: [internal]

  app:
    build: .
    env_file: .env.prod
    networks: [internal, edge]
    depends_on:
      postgres: { condition: service_healthy }
      qdrant: { condition: service_healthy }
      redis: { condition: service_started }

networks:
  internal:
    internal: true
  edge: {}
```

Avvio:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 2.2 Dockerfile dell'app

Non incluso in repo per scelta (deploy host-native default). Template suggerito:

```dockerfile
FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv pip install --system -e ".[hybrid,ingest,obs]"

FROM deps AS app
COPY . .
RUN useradd -r -u 1000 llmwiki && chown -R llmwiki /app
USER llmwiki

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

> Embedder + reranker scaricano modelli HuggingFace al primo avvio (~5GB). Pre-bake in image con `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"` per evitare cold-start lento.

## 3. Hardening checklist produzione

| Voce                       | Default sicuro                      | Verifica                                                       |
| -------------------------- | ----------------------------------- | -------------------------------------------------------------- |
| `SECRET_KEY`               | random ≥ 32 byte, **unica per env** | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `AUTH_REQUIRED`            | `true`                              | tutti gli endpoint user dietro login                           |
| `AUTH_PUBLIC_REGISTRATION` | `false`                             | solo invito                                                    |
| `AUTH_COOKIE_SECURE`       | `true`                              | richiede HTTPS                                                 |
| `AUTH_COOKIE_SAMESITE`     | `strict`                            | tranne se cross-domain                                         |
| `ENABLE_HSTS`              | `true`                              | dietro HTTPS                                                   |
| `SECURITY_HEADERS_ENABLED` | `true`                              | CSP attivo                                                     |
| `ADMIN_API_LOOPBACK_ONLY`  | `true`                              | + RBAC                                                         |
| `ADMIN_API_ENABLED`        | `false` se non necessario           | usa CLI sull'host                                              |
| `CORS_ALLOW_ORIGINS`       | dominio prod esatto, no wildcard    | —                                                              |
| `POSTGRES_PASSWORD`        | ≥ 24 char random                    | rotazione semestrale                                           |
| `CACHE_BACKEND`            | `redis` (multi-worker)              | rate-limit consistente                                         |
| `REDIS_PASSWORD`           | settata                             | + `requirepass`                                                |
| `LOG_FORMAT`               | `json`                              | aggregazione Loki                                              |
| `LOG_LEVEL_CONSOLE`        | `INFO`                              | mai `DEBUG` in prod                                            |
| `OTEL_TRACES_SAMPLER_ARG`  | 0.1                                 | bilanciamento costo/visibilità                                 |
| Backup Postgres            | giornaliero + WAL                   | testato (restore mensile)                                      |
| Backup Qdrant              | snapshot giornaliero                | + verifica                                                     |
| OS firewall                | porte solo 443 + SSH                | iptables/ufw                                                   |
| SSH                        | key-only, no root login             | —                                                              |
| Aggiornamenti OS           | `unattended-upgrades`               | settimanale                                                    |
| TLS                        | A+ ssllabs                          | Caddy auto Let's Encrypt                                       |

### Generare config CSP custom

Default CSP applicato dall'app è restrittivo (`default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, no inline-script). Vedi [`llm_wiki/config.py`](../llm_wiki/config.py) `_DEFAULT_CSP`. Se servi asset CDN, override:

```ini
CONTENT_SECURITY_POLICY="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.example.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://cdn.example.com; connect-src 'self' https://api.example.com; frame-ancestors 'none'"
```

### Reverse proxy template pronti

- Caddy: [`deploy/reverse-proxy/Caddyfile`](../deploy/reverse-proxy/Caddyfile) — TLS Let's Encrypt automatico, asset hashati con cache 1y immutable, `/api/admin*` 404 sul public, NDJSON streaming friendly (`flush_interval -1`).
- Nginx: [`deploy/reverse-proxy/nginx.conf`](../deploy/reverse-proxy/nginx.conf) — equivalente con `proxy_buffering off`, `client_max_body_size 100M` per ingest PDF, regex match sugli asset hashati.

### Log rotation

[`deploy/logrotate/llm-wiki`](../deploy/logrotate/llm-wiki) — daily rotate 30, copytruncate, SIGHUP all'unit attivo. Install: `sudo cp deploy/logrotate/llm-wiki /etc/logrotate.d/`.

## 4. Multi-domain (N pack, stesso host)

Pattern processi separati:

```txt
:8001 → APP_DOMAIN=legal     vaults/legal/
:8002 → APP_DOMAIN=medical   vaults/medical/
:8003 → APP_DOMAIN=technical vaults/technical/
```

Reverse proxy routing per host:

```caddy
legal.example.com  { reverse_proxy /api/* /auth/* 127.0.0.1:8001 }
medical.example.com { reverse_proxy /api/* /auth/* 127.0.0.1:8002 }
```

Ogni processo:

- Stesso Postgres (ma `tenant.slug` separati per logica admin cross-domain — futura).
- Qdrant condiviso (collection per `APP_DOMAIN` separate).
- `.env.<domain>` con `EnvironmentFile=` separato in systemd.

## 5. Aggiornamenti zero-downtime

```bash
# 1. Backup
pg_dump ... > /backups/pre-upgrade-$(date +%F).dump

# 2. Pull
cd /srv/llm-wiki/app && git fetch && git checkout v0.X.Y

# 3. Dipendenze
.venv/bin/pip install -e ".[hybrid,ingest,obs]"

# 4. Migrations (transazionali; safe)
.venv/bin/alembic upgrade head

# 5. Build frontend
cd frontend && npm ci && npm run build

# 6. Restart graceful
sudo systemctl reload llm-wiki  # SIGHUP → uvicorn reload workers
# oppure
curl -X POST http://127.0.0.1:8000/api/admin/runtime/restart \
  -H "Authorization: Bearer <admin-token>"
```

Reload graceful uvicorn esegue rolling restart dei worker; richieste in-flight finiscono entro `--timeout-graceful-shutdown` (default 30s).

## 6. Scaling

### Verticale (single host)

- RAM: BGE-M3 (~2GB) + reranker (~600MB) + LLM (8B → ~6GB su CPU, meno su GPU). 16GB minimo, 32GB consigliato.
- GPU: opzionale. Cuda detect via `EMBEDDER_DEVICE=cuda`. Se LLM su Ollama, dedica GPU separato per RAG vs ingest.
- Disco: vault testuale piccolo (MB); Qdrant cresce ~2KB/chunk × N chunk.

### Orizzontale

Richiede:

- **State condiviso**: Postgres + Qdrant centralizzati.
- **Rate limit distribuito**: `CACHE_BACKEND=redis` obbligatorio.
- **Sticky session**: NON necessario (JWT stateless + refresh cookie).
- **Sessione ingest**: job queue va spostato su Postgres/Redis se più worker (oggi in-memory). Workaround: dedicare un solo worker all'ingest, altri solo lettura.
- **File uploads**: spostare `raw/` su volume condiviso (NFS, EFS) o object storage (futuro).

## 7. TLS / certificati

Caddy: automatic via Let's Encrypt (default). Nessuna config extra necessaria.

Manuale:

```bash
certbot certonly --webroot -w /var/www -d wiki.example.com
# rinnovo via cron systemd-timer
```

Test cifre supportate:

```bash
testssl.sh wiki.example.com
```

Target: TLS 1.3 only, no compression, HSTS preload.

## 8. Backup & restore

Vedi [`operations.md`](operations.md) per script completi e cron. Sintesi:

| Cosa                   | Frequenza                              | Strumento                         |
| ---------------------- | -------------------------------------- | --------------------------------- |
| Postgres               | giornaliero (logical) + continuo (WAL) | `pg_dump` + `pg_basebackup`/wal-g |
| Qdrant                 | giornaliero                            | snapshot REST API                 |
| Vaults `wiki/`, `raw/` | giornaliero                            | `restic` o `rsync` su S3          |
| `.env` + Domain Packs  | settimanale                            | git-encrypt (sops) o vault        |

Test restore: **mensile, non opzionale**.

## 9. Disaster recovery

| Scenario            | RTO    | RPO            | Procedura                                |
| ------------------- | ------ | -------------- | ---------------------------------------- |
| Crash app           | 1 min  | 0              | systemd restart automatico               |
| Postgres corruption | 30 min | < 5 min (WAL)  | restore WAL su nuovo host                |
| Qdrant data loss    | 1 ora  | 24h (snapshot) | restore snapshot, eventualmente reingest |
| Total host loss     | 4 ore  | 24h            | provision nuovo host, IaC, restore       |

## 10. Compliance

- **GDPR**: vedi `auth-rbac.md` §10. Export utente: `GET /api/me/export` (ZIP). Erasure: `DELETE /api/admin/users/{id}` (cascade su tabelle isolated, audit anonymizzato).
- **Data residency**: tutti i dati in Postgres locale. LLM esterno (OpenAI) opzionale; per data-sovereignty usa Ollama o LLM self-hosted.
- **Logs**: nessun PII nei log applicativi (filter automatici); audit_events sì ma scoped.

## 11. Healthcheck endpoints

| Path         | Scopo     | Atteso                            |
| ------------ | --------- | --------------------------------- |
| `/health`    | liveness  | `200 OK` sempre se processo vivo  |
| `/healthz`   | readiness | 200 solo se pack + DB + Qdrant ok |
| `/readiness` | dettaglio | JSON con stato per dipendenza     |

Configurazione load balancer: usare `/healthz` (k8s-style).

## 12. Costo operativo orientativo

Riferimento single-host produzione:

| Risorsa                                 | Mese (EU cloud generico) |
| --------------------------------------- | ------------------------ |
| VM 8 vCPU 32GB RAM                      | ~80€                     |
| Postgres managed (small)                | ~25€                     |
| Qdrant Cloud (1GB)                      | ~25€                     |
| Backup S3 (100GB)                       | ~3€                      |
| LLM (Ollama self-hosted)                | 0                        |
| LLM (OpenAI gpt-4o-mini ~5M token/mese) | ~25€                     |

→ ~150€/mese/verticale, escluso GPU.
