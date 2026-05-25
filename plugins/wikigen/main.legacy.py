"""FastAPI server exposing the white-label wiki engine over HTTP.

Multi-tenancy: la wiki (filesystem + Qdrant collection) è SHARED fra
tutti gli utenti. Isolamento è a livello sessione utente — chat,
memorie (RAG personale), feedback. Ogni utente ha un proprio tenant
(invariante 1:1) gestito via JWT + refresh rotation, con anti-tampering
verifica DB nel TenantMiddleware. Wiki/Domain Pack è un ortogonale
"vertical preset" globale del processo.

Lifespan order
==============

1. Carica Domain Pack se ``APP_DOMAIN`` valorizzato (altrimenti setup mode).
2. Validate ``SECRET_KEY`` se ``AUTH_REQUIRED=true`` (fail-fast).
3. Apri pool Postgres + bootstrap admin se ``users`` vuota.
4. Warm core (embedder + collection); background warmup LLM/reranker.
5. Auto-ingest pending PDFs.

Shutdown: ``close_pool()`` esplicito.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_wiki import config
from llm_wiki.api.routers.chat import router as chat_router
from llm_wiki.api.routers.embed_public import router as embed_public_router
from llm_wiki.api.routers.feedback import router as feedback_router
from llm_wiki.api.routers.graph import router as graph_router
from llm_wiki.api.routers.health import router as health_router
from llm_wiki.api.routers.ingest import autostart_pending_ingest
from llm_wiki.api.routers.ingest import router as ingest_router
from llm_wiki.api.routers.metrics_router import router as metrics_router
from llm_wiki.api.routers.system import router as system_router
from llm_wiki.api.routers.wiki import router as wiki_router
from llm_wiki.domain.registry import load_pack
from llm_wiki.ingest_raw.jobs import get_registry
from llm_wiki.observability.http_middleware import HttpMetricsMiddleware
from llm_wiki.observability.logging_config import configure_logging
from llm_wiki.observability.request_id import RequestIdMiddleware
from llm_wiki.observability.tracing import setup_tracing
from llm_wiki.vectorstore.embedder import get_embedder
from llm_wiki.vectorstore.qdrant_ops import create_collection

# Logging: JSON quando deployato dietro Promtail/Loki (LOG_FORMAT=json),
# testo human-friendly in dev. Idempotente: l'import sotto pytest /
# uvicorn-reload non duplica handler.
configure_logging(
    level_console=os.getenv("LOG_LEVEL_CONSOLE", "INFO"),
    level_file=os.getenv("LOG_LEVEL_FILE", "INFO"),
    log_format=os.getenv("LOG_FORMAT"),
)
logger = logging.getLogger(__name__)


def _check_vault_pack_marker(pack_name: str, vault_root: Path) -> None:
    """Detect cross-pack vault collisions at boot.

    Each vault carries a ``.pack-id`` marker (written by scaffold + here
    on first boot). If the marker disagrees with the active pack name we
    log a loud warning: the user has likely swapped ``APP_DOMAIN``
    manually without realigning ``WIKI_ROOT``, so RAG/ingest will read
    and write into another pack's wiki/raw tree.
    """
    marker = vault_root / ".pack-id"
    try:
        if marker.exists():
            recorded = marker.read_text(encoding="utf-8").strip()
            if recorded and recorded != pack_name:
                logger.warning(
                    "[startup] VAULT/PACK MISMATCH: vault %s carries pack-id=%r "
                    "but APP_DOMAIN=%r — RAG/ingest will operate on the wrong pack's "
                    "data. Use the wizard /api/admin/tenants/{name}/activate to "
                    "realign WIKI_ROOT, or edit .env so APP_DOMAIN=%s.",
                    vault_root,
                    recorded,
                    pack_name,
                    recorded,
                )
                return
        else:
            vault_root.mkdir(parents=True, exist_ok=True)
            marker.write_text(pack_name + "\n", encoding="utf-8")
    except OSError as exc:
        logger.debug("[startup] pack-id marker check skipped: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Boot order: pack → secret/DB → bootstrap admin → core warmup → autostart.

    First-run path: ``APP_DOMAIN`` unset = setup mode (admin/scaffold
    reachable, RAG/ingest in 503). ``AUTH_REQUIRED`` senza ``SECRET_KEY``
    = fail-fast (boot non parte).
    """
    if config.APP_DOMAIN:
        try:
            pack = load_pack()
            logger.info("[startup] domain pack: %s (%s)", pack.name, pack.label)
            _check_vault_pack_marker(pack.name, Path(config.WIKI_ROOT))
        except Exception as exc:
            logger.error("[startup] pack load failed: %s — admin API still reachable", exc)
    else:
        logger.warning(
            "[startup] APP_DOMAIN unset — running in setup mode. "
            "Open the UI and complete the wizard, or run `wiki-wl init --domain <name>`."
        )

    # Auth gate: SECRET_KEY obbligatoria con AUTH_REQUIRED. Fail-fast
    # invece di sicurezza compromessa dopo qualche request.
    if config.AUTH_REQUIRED and not (config.SECRET_KEY or "").strip():
        raise RuntimeError(
            "AUTH_REQUIRED=true ma SECRET_KEY vuota. Genera con "
            '`python -c "import secrets; print(secrets.token_urlsafe(48))"` '
            "e imposta in .env."
        )

    # DB pool: open + bootstrap admin se Postgres abilitato.
    if config.POSTGRES_ENABLED:
        try:
            from llm_wiki.auth.bootstrap import bootstrap_admin_if_empty
            from llm_wiki.db.connection import health_check

            if health_check():
                logger.info("[startup] DB ready")
                bootstrap_admin_if_empty(vault_root=Path(config.WIKI_ROOT))
            else:
                logger.warning("[startup] DB health_check fail — auth/conv/memories diranno 503")
        except Exception as exc:
            logger.error("[startup] DB init failed: %s", exc)

    t0 = time.perf_counter()
    get_registry().set_loop(asyncio.get_running_loop())

    async def _preload_blocking() -> None:
        """Warmup necessari prima di servire richieste: embedder + collection.
        Tutto il resto (LLM warmup, reranker, examples cache) → fire-and-forget."""
        await asyncio.to_thread(get_embedder)
        await asyncio.to_thread(create_collection)

    async def _preload_background() -> None:
        """Warmup non-bloccanti. Se falliscono o sono lenti, /api resta servito."""
        from llm_wiki.utils.llm import warmup_llm
        from llm_wiki.vectorstore.reranker import rerank

        try:
            await asyncio.to_thread(
                rerank, "warmup", [{"score": 1.0, "payload": {"raw_text": "ping"}}], top_k=1
            )
        except Exception as exc:
            logger.debug("[startup] reranker warmup skipped: %s", exc)
        if config.APP_DOMAIN:
            try:
                await asyncio.to_thread(warmup_llm, config.INGEST_OLLAMA_MODEL)
            except Exception as exc:
                logger.warning("[startup] LLM warmup failed: %s", exc)
            try:
                from llm_wiki.ingest_raw.examples import _load_candidates

                await asyncio.to_thread(_load_candidates)
            except Exception as exc:
                logger.debug("[startup] examples preload skipped: %s", exc)

    try:
        await _preload_blocking()
        logger.info("[startup] core warmup done in %.2fs", time.perf_counter() - t0)
    except Exception as exc:
        logger.warning("[startup] partial warmup: %s", exc)

    # LLM warmup + examples preload girano in background: lifespan
    # ritorna subito, /api serve istantaneamente, modello si scalda
    # mentre l'utente naviga la UI. Senza questo, un Ollama unreachable
    # blocca 80s+ il boot e la UI sembra rotta.
    asyncio.create_task(_preload_background())

    # Auto-ingest pending PDFs deposited by the wizard's "Documenti" step.
    # Triggered only when `AUTO_INGEST_ON_STARTUP` is true (default true)
    # and the runtime has an active pack — otherwise ingest pipeline has
    # no domain knowledge to drive page generation.
    if config.APP_DOMAIN and getattr(config, "AUTO_INGEST_ON_STARTUP", True):
        try:
            await autostart_pending_ingest()
        except Exception as exc:
            logger.warning("[startup] autostart ingest skipped: %s", exc)

    yield

    # Shutdown: chiudi pool DB esplicito (psycopg_pool fa GC altrimenti
    # ma a uvicorn --reload può loggare warnings).
    if config.POSTGRES_ENABLED:
        try:
            from llm_wiki.db.connection import close_pool

            close_pool()
        except Exception as exc:
            logger.warning("[shutdown] close_pool: %s", exc)
    logger.info("[shutdown] bye")


app = FastAPI(title="Wiki White-Label API", version="0.1.0", lifespan=lifespan)

# OpenTelemetry: opt-in via OTEL_EXPORTER_OTLP_ENDPOINT. No-op altrimenti.
# Va prima di add_middleware perché FastAPIInstrumentor wrappa la callable.
try:
    setup_tracing(app)
except Exception as exc:  # pragma: no cover
    logger.warning("[startup] OpenTelemetry setup fallito (continuo senza): %s", exc)

# Middleware order: l'ULTIMO add_middleware è il PIÙ ESTERNO (Starlette
# inverte l'ordine di registrazione). Ordine effettivo wrapping:
#
#   request → RequestId → CORS → SecurityHeaders → TenantMiddleware
#                                                  → HttpMetrics → routes
#
# Registriamo dal più interno al più esterno.
app.add_middleware(HttpMetricsMiddleware)

if config.POSTGRES_ENABLED:
    from llm_wiki.auth.middleware import (
        EmbedCORSMiddleware,
        SecurityHeadersMiddleware,
        TenantMiddleware,
    )

    app.add_middleware(TenantMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

# CORS più esterno DOPO RequestId: il preflight non deve generare un
# UUID nuovo per ogni OPTIONS, ma vogliamo comunque header echo. Mettiamo
# CORS interno a RequestId — preflight risponde immediatamente, RequestId
# ha già aggiunto X-Request-ID alla response.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Tenant-ID", "X-Request-ID"],
)

# EmbedCORS REGISTRATO DOPO CORSMiddleware statico → girando in
# Starlette al contrario, EmbedCORS è MORE OUTER. Intercetta i preflight
# OPTIONS verso ``/api/embed/*`` PRIMA che lo CORS statico li 400-i
# (origin non in allowlist SPA). Path-prefix narrow: gli altri preflight
# scendono al CORSMiddleware statico invariati.
if config.POSTGRES_ENABLED:
    app.add_middleware(EmbedCORSMiddleware)

# RequestIdMiddleware = outermost: ogni request (anche errori middleware
# downstream) riceve un ID propagato a logs + traces.
app.add_middleware(RequestIdMiddleware)


# --- public routers --------------------------------------------------------

app.include_router(system_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(wiki_router)
app.include_router(chat_router)
app.include_router(feedback_router)
# Embed pubblico: token-authenticated, no JWT. Sempre montato — gli
# endpoint rispondono 503 se POSTGRES_ENABLED=false (tabella ``embeds``
# senza Postgres non esiste).
app.include_router(embed_public_router)
app.include_router(ingest_router)
# Knowledge graph (graphify-inspired). Router always mounted; endpoints
# return 503 internally if GRAPH_DB_ENABLED=false or FalkorDB unreachable
# — keeps the API surface stable for the frontend.
app.include_router(graph_router)

# Auth + tenant-scoped routers (solo con Postgres). Senza DB
# conversations/memories non hanno backing storage — meglio 404 che
# 503 su ogni request in setup mode.
if config.POSTGRES_ENABLED:
    from llm_wiki.api.routers.auth import router as auth_router
    from llm_wiki.api.routers.conversations import router as conversations_router
    from llm_wiki.api.routers.embeds_admin import router as embeds_admin_router
    from llm_wiki.api.routers.feedback_admin import router as feedback_admin_router
    from llm_wiki.api.routers.gdpr import router as gdpr_router
    from llm_wiki.api.routers.memories import router as memories_router
    from llm_wiki.api.routers.rbac import router as rbac_router
    from llm_wiki.api.routers.rbac_groups import router as rbac_groups_router
    from llm_wiki.api.routers.rbac_lifecycle import router as rbac_lifecycle_router

    app.include_router(auth_router)
    app.include_router(conversations_router)
    app.include_router(memories_router)
    app.include_router(rbac_router)
    app.include_router(rbac_lifecycle_router)
    app.include_router(rbac_groups_router)
    app.include_router(gdpr_router)
    app.include_router(embeds_admin_router)
    app.include_router(feedback_admin_router)
    logger.info(
        "[startup] auth+conversations+memories+rbac+groups+gdpr mounted "
        "(public_registration=%s)",
        config.AUTH_PUBLIC_REGISTRATION,
    )


# --- admin router (gated) --------------------------------------------------

if config.ADMIN_API_ENABLED:
    import ipaddress as _ipaddress

    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    from llm_wiki.api.admin import router as admin_router

    # Headers che possono spoofare client.host se l'app gira dietro un
    # proxy mal-configurato (uvicorn --proxy-headers o reverse proxy che
    # non rimuove gli header in ingresso). In setup mode rifiutiamo
    # qualunque richiesta admin che li presenti — preferiamo un 403
    # leggibile a un bypass silenzioso.
    _PROXY_HEADER_NAMES = ("x-forwarded-for", "forwarded", "x-real-ip", "x-client-ip")

    def _is_loopback_client(host: str | None) -> bool:
        if not host:
            return False
        # IPv6 mapped IPv4 (es. ::ffff:127.0.0.1) coperto da is_loopback.
        try:
            return _ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    class _AdminGateMiddleware(BaseHTTPMiddleware):
        """Gating per ``/api/admin/*`` (Fase 4 multi-tenancy).

        Due strategie coesistono:

        - **Postgres ON** (deploy normale): JWT bearer con ``role=admin``
          richiesto e verificato router-side via ``require_admin``.
          Loopback opzionale come hardening aggiuntivo
          (defense-in-depth) — entrambi devono passare se attivati.
        - **Postgres OFF** (setup mode iniziale, no DB ancora): solo
          loopback consentito. Permette al wizard di girare al primo
          boot prima che esista qualunque utente DB.

        Hardening:
        - ``client.host`` validato via ``ipaddress.is_loopback`` invece
          di string-match (copre ``::ffff:127.0.0.1`` e rifiuta
          ``"localhost"`` come stringa).
        - Header proxy (``X-Forwarded-For``/``Forwarded``/``X-Real-IP``)
          rifiutati in setup mode: indicano che la richiesta è passata
          per un proxy e ``client.host`` potrebbe essere stato
          riscritto. Se servono per deploy reali, abilitare bearer admin
          (Postgres ON) e disattivare il loopback gate.
        """

        async def dispatch(self, request: Request, call_next):  # type: ignore[override]
            path = request.url.path
            if not path.startswith("/api/admin"):
                return await call_next(request)

            if config.ADMIN_API_LOOPBACK_ONLY:
                client_host = request.client.host if request.client else None
                has_bearer = request.headers.get("authorization", "").lower().startswith("bearer ")
                # Se Postgres ON e bearer presente → require_admin verifica
                # tutto router-side. Senza bearer → loopback obbligatorio
                # (fail-closed in setup mode).
                if not (config.POSTGRES_ENABLED and has_bearer):
                    proxy_header = next(
                        (h for h in _PROXY_HEADER_NAMES if h in request.headers),
                        None,
                    )
                    if proxy_header is not None or not _is_loopback_client(client_host):
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": (
                                    "admin endpoints richiedono loopback "
                                    "(setup mode) o bearer admin (deploy)."
                                )
                            },
                        )
            return await call_next(request)

    app.add_middleware(_AdminGateMiddleware)

    app.include_router(admin_router)
    logger.info(
        "[startup] admin API mounted (loopback=%s, postgres=%s)",
        config.ADMIN_API_LOOPBACK_ONLY,
        config.POSTGRES_ENABLED,
    )


if __name__ == "__main__":
    import uvicorn

    config.print_banner()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
