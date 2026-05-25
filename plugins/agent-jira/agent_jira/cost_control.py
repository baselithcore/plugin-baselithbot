"""
Modulo per il controllo dei costi computazionali (Phase 1).
Gestisce budget per token LLM e query GraphDB per singola richiesta.
"""

import contextvars
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Configurazioni
from agent_jira.config import (
    AGENT_MAX_TOKENS,
    COST_CONTROL_ENABLED,
    GRAPH_MAX_HOPS,
    GRAPH_QUERY_LIMIT,
)

logger = logging.getLogger(__name__)


@dataclass
class CostStats:
    """Statistiche di costo per la richiesta corrente."""

    tokens_used: int = 0
    graph_queries: int = 0
    start_time: float = field(default_factory=time.time)
    # Log dettagliato per debug/audit
    queries_log: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "tokens_used": self.tokens_used,
            "graph_queries": self.graph_queries,
            "duration": round(time.time() - self.start_time, 3),
        }


# ContextVar per isolare le statistiche per richiesta
_cost_context: contextvars.ContextVar[Optional[CostStats]] = contextvars.ContextVar(
    "cost_stats", default=None
)


class CostController:
    """
    Controller singleton-like per tracciare e limitare i costi.
    Usa contextvars per gestire lo stato thread-safe/async-safe.
    """

    @staticmethod
    def initialize() -> None:
        """Inizializza un nuovo contatore per il contesto corrente."""
        _cost_context.set(CostStats())

    @staticmethod
    @contextmanager
    def unbounded(reason: str = "batch") -> Iterator[None]:
        """
        Sospende il tracking dei costi nel blocco corrente.

        Da usare per operazioni batch/background (indexing, bootstrap,
        migrazioni) che non devono essere vincolate al budget per-request.
        Reimposta il CostStats precedente all'uscita.
        """
        token = _cost_context.set(None)
        logger.debug(f"CostController: tracking sospeso ({reason})")
        try:
            yield
        finally:
            _cost_context.reset(token)

    @staticmethod
    def get_stats() -> Optional[CostStats]:
        """Recupera le statistiche correnti (se inizializzate)."""
        return _cost_context.get()

    @staticmethod
    def track_tokens(count: int, model: str = "unknown") -> None:
        """
        Incrementa il contatore token per-request + accumula nel budget
        giornaliero per-tenant (Sprint 12).

        Solleva BudgetExceededError su limit per-request.
        """
        stats = _cost_context.get()
        if stats and COST_CONTROL_ENABLED:
            stats.tokens_used += count
            if stats.tokens_used > AGENT_MAX_TOKENS:
                logger.error(
                    f"🛑 BUDGET EXCEEDED: Tokens {stats.tokens_used} > {AGENT_MAX_TOKENS}"
                )
                raise BudgetExceededError(
                    f"Token limit exceeded: {stats.tokens_used}/{AGENT_MAX_TOKENS}"
                )

        # Sprint 12: accumula su budget giornaliero per-tenant (Redis counter).
        try:
            from agent_jira.quotas import quota_tracker

            quota_tracker.track_llm_tokens(count)
        except Exception:
            pass

    @staticmethod
    def track_query(cypher: str) -> None:
        """
        Traccia una query al grafo.
        Valida la query per evitare scan globali e controlla il limite numerico.
        """
        stats = _cost_context.get()
        if not stats or not COST_CONTROL_ENABLED:
            return

        # 1. Incrementa count
        stats.graph_queries += 1
        stats.queries_log.append(cypher[:100] + "..." if len(cypher) > 100 else cypher)

        # 2. Check budget numerico
        if stats.graph_queries > GRAPH_QUERY_LIMIT:
            logger.error(
                f"🛑 BUDGET EXCEEDED: Graph Queries {stats.graph_queries} > {GRAPH_QUERY_LIMIT}"
            )
            raise BudgetExceededError(
                f"Graph query limit exceeded: {stats.graph_queries}/{GRAPH_QUERY_LIMIT}"
            )

        # 3. Validazione Pattern proibiti (Phase 1: Block global/unbounded)
        # Blocca query senza WHERE o filtri specifici se sembrano scansioni intero DB
        # Esempio banale: "MATCH (n) RETURN n"
        stripped = cypher.strip().upper()
        if "MATCH (N) RETURN N" in stripped or "MATCH (N) DETACH DELETE N" in stripped:
            # Check lasco per ora, migliorerà in Phase 2
            if "WHERE" not in stripped and "LIMIT" not in stripped:
                logger.warning(f"⚠️ Potentially unbounded query detected: {cypher}")
                # Per ora logghiamo warning, in futuro raise

    @staticmethod
    def check_hops(hops: int) -> None:
        """Verifica che la profondità di traversal non superi il limite."""
        if not COST_CONTROL_ENABLED:
            return

        if hops > GRAPH_MAX_HOPS:
            logger.error(f"🛑 TRAVERSAL LIMIT: Hops {hops} > {GRAPH_MAX_HOPS}")
            raise BudgetExceededError(
                f"Max hop limit exceeded: {hops}/{GRAPH_MAX_HOPS}"
            )


class BudgetExceededError(Exception):
    """Eccezione sollevata quando si supera un limite di budget."""

    pass


class CostControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware che inizializza il tracking dei costi all'inizio della richiesta
    e logga il report finale.
    """

    async def dispatch(self, request: Request, call_next):
        # 1. Inizializza il tracking
        CostController.initialize()

        try:
            response = await call_next(request)
            return response
        except BudgetExceededError as e:
            # Intercetta errori di budget e ritorna 429 o 400
            logger.warning(f"Cost limit blocked request: {e}")
            return JSONResponse(
                status_code=429, content={"error": "Quota exceeded", "message": str(e)}
            )
        finally:
            stats = CostController.get_stats()
            if stats:
                path = request.url.path
                # Evita di loggare ping di health/heartbeat che hanno costo 0, per non spammare
                if (
                    stats.tokens_used == 0
                    and stats.graph_queries == 0
                    and ("health" in path or "heartbeat" in path)
                ):
                    pass
                else:
                    logger.info(
                        f"💰 COST REPORT [{request.method} {path}]: "
                        f"Tokens={stats.tokens_used}, DB_Queries={stats.graph_queries}, "
                        f"Time={round(time.time() - stats.start_time, 3)}s"
                    )


# Hook globale per facilitare import e usage
cost_controller = CostController()
