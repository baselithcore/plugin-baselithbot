"""Static config: tunables that don't depend on the active tenant.

Anything that references ``APP_DOMAIN`` / ``WIKI_ROOT`` / ``COLLECTION_NAME``
at import time stays in ``config/__init__.py`` so ``refresh_paths()`` can
update them on the fly.
"""

from __future__ import annotations

from llm_wiki.config._coerce import _bool, _float, _int, _optional_str, _str

# --- LLM general -----------------------------------------------------------

LLM_TIMEOUT = _float("LLM_TIMEOUT", 600.0)
# Ollama keep_alive: how long the daemon retains the model in RAM after a
# request. Default `30m` means subsequent calls skip the cold-start cost
# (model load can take 30-60s for 8B+ params). `0` evicts immediately,
# `-1m`/`infinity` keeps it loaded forever.
LLM_KEEP_ALIVE = _str("LLM_KEEP_ALIVE", "30m")

# Ollama `num_ctx`: lunghezza massima del context window in token.
INGEST_OLLAMA_NUM_CTX = max(0, _int("INGEST_OLLAMA_NUM_CTX", 8192))
# Budget caratteri del dump "verbatim atoms" iniettato nel prompt
# (vedi ``planner.extract_verbatim_atoms``).
INGEST_VERBATIM_MAX_CHARS = max(0, _int("INGEST_VERBATIM_MAX_CHARS", 6000))
# Soglia caratteri/pagina sopra la quale un PDF è "text-only" → fast-path.
INGEST_SKIP_DOCLING_THRESHOLD = max(0, _int("INGEST_SKIP_DOCLING_THRESHOLD", 800))
INGEST_BATCH_CLASSIFY_PLAN = _bool("INGEST_BATCH_CLASSIFY_PLAN", True)
INGEST_CRITIC_MAX_ITER = max(1, _int("INGEST_CRITIC_MAX_ITER", 1))


# --- embeddings ------------------------------------------------------------

EMBEDDER_MODEL = _str("EMBEDDER_MODEL", "BAAI/bge-m3")
EMBEDDER_FORCE_LEGACY = _bool("EMBEDDER_FORCE_LEGACY", False)
EMBEDDER_DEVICE = _str("EMBEDDER_DEVICE", "auto").lower()
EMBEDDER_BATCH_SIZE = max(1, _int("EMBEDDER_BATCH_SIZE", 32))
EMBEDDER_USE_FP16 = _bool("EMBEDDER_USE_FP16", True)
EMBEDDER_URL = _optional_str("EMBEDDER_URL")
EMBEDDER_HTTP_TIMEOUT = _float("EMBEDDER_HTTP_TIMEOUT", 120.0)
LEGACY_EMBEDDER_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OFFLINE_MODE = _bool("OFFLINE_MODE", False)


# --- vector store ----------------------------------------------------------

QDRANT_MODE = _str("QDRANT_MODE", "embedded").lower()
QDRANT_URL = _str("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = _optional_str("QDRANT_API_KEY")

HYBRID_ENABLED = _bool("HYBRID_ENABLED", True)
HYBRID_USE_COLBERT = _bool("HYBRID_USE_COLBERT", True)
HYBRID_PREFETCH_LIMIT = max(5, _int("HYBRID_PREFETCH_LIMIT", 50))

if _bool("HYBRID_USE_COLBERT", True):
    _default_upsert_batch = 4
elif _bool("HYBRID_ENABLED", True):
    _default_upsert_batch = 16
else:
    _default_upsert_batch = 64
QDRANT_UPSERT_BATCH_SIZE = max(
    1, _int("QDRANT_UPSERT_BATCH_SIZE", _default_upsert_batch)
)
QDRANT_TIMEOUT = max(5.0, _float("QDRANT_TIMEOUT", 60.0))
QDRANT_PREFER_GRPC = _bool("QDRANT_PREFER_GRPC", False)
QDRANT_GRPC_PORT = max(1, _int("QDRANT_GRPC_PORT", 6334))


# --- reranker --------------------------------------------------------------

RERANKER_ENABLED = _bool("RERANKER_ENABLED", True)
RERANKER_MODEL = _str("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
RERANKER_INPUT_MULT = max(2, _int("RERANKER_INPUT_MULT", 5))
RERANKER_DEVICE = _str("RERANKER_DEVICE", "auto").lower()
RERANKER_BATCH_SIZE = max(1, _int("RERANKER_BATCH_SIZE", 32))


# --- MMR -------------------------------------------------------------------

MMR_ENABLED = _bool("MMR_ENABLED", True)
MMR_LAMBDA = max(0.0, min(1.0, _float("MMR_LAMBDA", 0.7)))


# --- citation validation ---------------------------------------------------

CITATION_VALIDATION_ENABLED = _bool("CITATION_VALIDATION_ENABLED", True)
CITATION_STRICT_GROUNDING = _bool("CITATION_STRICT_GROUNDING", True)
CITATION_REPAIR_ENABLED = _bool("CITATION_REPAIR_ENABLED", False)
CITATION_ANCHOR_VALIDATION_ENABLED = _bool("CITATION_ANCHOR_VALIDATION_ENABLED", False)


# --- RAG sampling + guards -------------------------------------------------

RAG_TEMPERATURE = max(0.0, min(2.0, _float("RAG_TEMPERATURE", 0.1)))
RAG_TOP_P = max(0.0, min(1.0, _float("RAG_TOP_P", 0.9)))
RAG_NUM_PREDICT = _int("RAG_NUM_PREDICT", -1)
RAG_SEED = _int("RAG_SEED", 0)

RAG_INTENT_GUARD_ENABLED = _bool("RAG_INTENT_GUARD_ENABLED", True)

RAG_GROUNDEDNESS_ENABLED = _bool("RAG_GROUNDEDNESS_ENABLED", False)
RAG_GROUNDEDNESS_MIN = max(0.0, min(1.0, _float("RAG_GROUNDEDNESS_MIN", 0.95)))
RAG_GROUNDEDNESS_REPAIR = _bool("RAG_GROUNDEDNESS_REPAIR", False)
RAG_GROUNDEDNESS_MODEL = _str("RAG_GROUNDEDNESS_MODEL", "")

RAG_CODE_BLOCK_GUARD_ENABLED = _bool("RAG_CODE_BLOCK_GUARD_ENABLED", True)
RAG_CODE_BLOCK_STRIP = _bool("RAG_CODE_BLOCK_STRIP", False)

RAG_NUMERIC_GUARD_ENABLED = _bool("RAG_NUMERIC_GUARD_ENABLED", True)
RAG_NUMERIC_GUARD_INCLUDE_GENERIC = _bool("RAG_NUMERIC_GUARD_INCLUDE_GENERIC", False)
RAG_NUMERIC_STRIP = _bool("RAG_NUMERIC_STRIP", False)


# --- conversational memory (history-aware retrieval) -----------------------
# Quando una conversazione persistita ha turni precedenti, riscrive la
# domanda in forma "standalone" PRIMA del retrieval. Senza questo step,
# follow-up tipo "approfondiscilo" / "e per la v3?" / "perché?" arrivano
# al retrieval come query nude e recuperano nulla — modello inventa o
# dichiara assenza falsa. Pattern allineato a LangChain
# ``create_history_aware_retriever`` e LlamaIndex ``CondenseQuestion``.
#
# Default ON quando Postgres è attivo (utente loggato → memoria
# autoritativa server-side). Chat anonima legacy resta inalterata.
RAG_HISTORY_CONDENSE_ENABLED = _bool(
    "RAG_HISTORY_CONDENSE_ENABLED",
    _bool(
        "POSTGRES_ENABLED",
        bool(_optional_str("DATABASE_URL") or _optional_str("POSTGRES_HOST")),
    ),
)
# Modello dedicato al condensing. Vuoto = fallback su RAG vendor default
# (OLLAMA_MODEL / OPENAI_MODEL). Task tipico è 1-shot piccolo → un
# modello "fast" è sufficiente (qwen2.5:3b / gpt-4o-mini).
RAG_HISTORY_CONDENSE_MODEL = _str("RAG_HISTORY_CONDENSE_MODEL", "")
# Cap turni inclusi nel condense prompt. Più alto = più contesto ma più
# token e latency. 6 = ultimi 3 round (user+assistant) — sweet spot.
RAG_HISTORY_CONDENSE_MAX_TURNS = max(2, _int("RAG_HISTORY_CONDENSE_MAX_TURNS", 6))
# Trunc per-turno (char) usato sia da condense che da
# ``build_history_block``. Difende il context window in chat lunghe.
RAG_HISTORY_TURN_MAX_CHARS = max(200, _int("RAG_HISTORY_TURN_MAX_CHARS", 800))
# Lunghezza massima della query riscritta. Difende contro modelli che
# rispondono con un mini-saggio invece di una query.
RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS = max(
    40, _int("RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS", 400)
)


# --- query understanding ---------------------------------------------------

HYDE_ENABLED = _bool("HYDE_ENABLED", False)
HYDE_MAX_TOKENS = max(50, _int("HYDE_MAX_TOKENS", 200))

QUERY_DECOMPOSITION_ENABLED = _bool("QUERY_DECOMPOSITION_ENABLED", False)
QUERY_DECOMPOSITION_MAX_SUBS = max(1, min(6, _int("QUERY_DECOMPOSITION_MAX_SUBS", 3)))


# --- contextual retrieval --------------------------------------------------

CONTEXTUAL_ENABLED = _bool("CONTEXTUAL_ENABLED", False)
CONTEXTUAL_LLM_MODEL = _str("CONTEXTUAL_LLM_MODEL", "qwen2.5:7b-instruct")
CONTEXTUAL_MAX_TOKENS = max(50, _int("CONTEXTUAL_MAX_TOKENS", 120))
CONTEXTUAL_CONCURRENCY = max(1, _int("CONTEXTUAL_CONCURRENCY", 6))


# --- graph (tenant-independent) --------------------------------------------

GRAPH_DB_ENABLED = _bool("GRAPH_DB_ENABLED", False)
GRAPH_DB_URL = _str("GRAPH_DB_URL", "redis://localhost:6379")
GRAPH_DB_TIMEOUT = _float("GRAPH_DB_TIMEOUT", 5.0)

GRAPH_EXTRACT_ENABLED = _bool("GRAPH_EXTRACT_ENABLED", False)
GRAPH_RAG_ENABLED = _bool("GRAPH_RAG_ENABLED", False)
GRAPH_CHUNK_ENTITY_TAGGING_ENABLED = _bool("GRAPH_CHUNK_ENTITY_TAGGING_ENABLED", False)
GRAPH_RAG_HOPS = max(1, min(3, _int("GRAPH_RAG_HOPS", 1)))
GRAPH_RAG_MAX_EXTRA_PAGES = max(0, _int("GRAPH_RAG_MAX_EXTRA_PAGES", 3))
GRAPH_CONFIDENCE_MIN = max(0.0, min(1.0, _float("GRAPH_CONFIDENCE_MIN", 0.5)))

GRAPH_LEIDEN_RESOLUTION = max(0.1, _float("GRAPH_LEIDEN_RESOLUTION", 1.0))
GRAPH_PAGERANK_ALPHA = max(0.05, min(0.99, _float("GRAPH_PAGERANK_ALPHA", 0.85)))
GRAPH_CENTRALITY_TOP_N = max(1, _int("GRAPH_CENTRALITY_TOP_N", 25))


# --- retrieval tuning ------------------------------------------------------

RETRIEVAL_TOP_K = max(1, _int("RETRIEVAL_TOP_K", 8))
CHUNK_SIZE = max(100, _int("CHUNK_SIZE", 700))
CHUNK_OVERLAP = max(0, _int("CHUNK_OVERLAP", 120))

INGEST_SUPPORTED_EXTENSIONS_RAW = _str(
    "INGEST_SUPPORTED_EXTENSIONS",
    ".pdf,.docx,.pptx,.html,.htm,.md,.xlsx,.png,.jpg,.jpeg,.tiff",
)
INGEST_SUPPORTED_EXTENSIONS = frozenset(
    ext.strip().lower()
    for ext in INGEST_SUPPORTED_EXTENSIONS_RAW.split(",")
    if ext.strip().startswith(".")
)

AGENTIC_RAG_ENABLED = _bool("AGENTIC_RAG_ENABLED", False)
AGENTIC_RAG_MAX_ITERATIONS = max(1, min(5, _int("AGENTIC_RAG_MAX_ITERATIONS", 2)))
AGENTIC_RAG_REFLECT_ENABLED = _bool("AGENTIC_RAG_REFLECT_ENABLED", True)
AGENTIC_RAG_PLANNER_MAX_SUBQUERIES = max(
    1, min(5, _int("AGENTIC_RAG_PLANNER_MAX_SUBQUERIES", 3))
)

HIERARCHICAL_CHUNKING_ENABLED = _bool("HIERARCHICAL_CHUNKING_ENABLED", False)
HIERARCHICAL_RETRIEVAL_ENABLED = _bool("HIERARCHICAL_RETRIEVAL_ENABLED", False)
HIERARCHICAL_PARENT_SIZE = max(400, _int("HIERARCHICAL_PARENT_SIZE", 1800))
HIERARCHICAL_CHILD_SIZE = max(100, _int("HIERARCHICAL_CHILD_SIZE", 400))
HIERARCHICAL_CHILD_OVERLAP = max(0, _int("HIERARCHICAL_CHILD_OVERLAP", 60))

QUERY_FILTER_INFERENCE_ENABLED = _bool("QUERY_FILTER_INFERENCE_ENABLED", False)
QUERY_FILTER_INFERENCE_STRICT_ONLY = _bool("QUERY_FILTER_INFERENCE_STRICT_ONLY", True)

PARENT_RETRIEVAL_ENABLED = _bool("PARENT_RETRIEVAL_ENABLED", True)
PARENT_RETRIEVAL_MAX_EXTRA = max(0, _int("PARENT_RETRIEVAL_MAX_EXTRA", 6))
PARENT_RETRIEVAL_PER_HIT_CAP = max(0, _int("PARENT_RETRIEVAL_PER_HIT_CAP", 3))


# --- cache TTL -------------------------------------------------------------

LLM_CACHE_TTL = _float("LLM_CACHE_TTL", 3600.0)
EMBEDDING_CACHE_TTL = _float("EMBEDDING_CACHE_TTL", 86400.0)


# --- retrieval performance -------------------------------------------------

RETRIEVAL_PARALLEL_ENABLED = _bool("RETRIEVAL_PARALLEL_ENABLED", True)
RETRIEVAL_PARALLEL_MAX_WORKERS = max(1, _int("RETRIEVAL_PARALLEL_MAX_WORKERS", 8))

QUERY_EMBED_CACHE_SIZE = max(0, _int("QUERY_EMBED_CACHE_SIZE", 256))

AGENTIC_RAG_PARALLEL_SEARCHES = _bool("AGENTIC_RAG_PARALLEL_SEARCHES", True)


# --- feedback (toggle) -----------------------------------------------------

FEEDBACK_ENABLED = _bool("FEEDBACK_ENABLED", True)


# --- Postgres + auth -------------------------------------------------------

POSTGRES_ENABLED = _bool(
    "POSTGRES_ENABLED",
    bool(_optional_str("DATABASE_URL") or _optional_str("POSTGRES_HOST")),
)
DB_POOL_MIN_SIZE = max(1, _int("DB_POOL_MIN_SIZE", 1))
DB_POOL_MAX_SIZE = max(DB_POOL_MIN_SIZE, _int("DB_POOL_MAX_SIZE", 10))
DB_POOL_TIMEOUT = max(1.0, _float("DB_POOL_TIMEOUT", 30.0))
APP_TIMEZONE_NAME = _str("APP_TIMEZONE", "UTC")

SECRET_KEY = _optional_str("SECRET_KEY")

AUTH_REQUIRED = _bool("AUTH_REQUIRED", False)
AUTH_PUBLIC_REGISTRATION = _bool("AUTH_PUBLIC_REGISTRATION", False)
AUTH_COOKIE_SECURE = _bool("AUTH_COOKIE_SECURE", True)
AUTH_COOKIE_SAMESITE = _str("AUTH_COOKIE_SAMESITE", "strict").lower()
ACCESS_TOKEN_TTL_MINUTES = max(1, _int("ACCESS_TOKEN_TTL_MINUTES", 1440))
REFRESH_TOKEN_TTL_DAYS = max(1, _int("REFRESH_TOKEN_TTL_DAYS", 30))
MULTI_TENANT_REQUIRED = _bool("MULTI_TENANT_REQUIRED", AUTH_REQUIRED)

ADMIN_BOOTSTRAP_EMAIL = _optional_str("ADMIN_BOOTSTRAP_EMAIL")
ADMIN_BOOTSTRAP_PASSWORD = _optional_str("ADMIN_BOOTSTRAP_PASSWORD")
ADMIN_BOOTSTRAP_AUTOSTART = _bool("ADMIN_BOOTSTRAP_AUTOSTART", False)

INVITATION_TTL_HOURS = max(1, _int("INVITATION_TTL_HOURS", 24))

RATE_LIMIT_USER_PER_MINUTE = max(0, _int("RATE_LIMIT_USER_PER_MINUTE", 120))
RATE_LIMIT_ADMIN_PER_MINUTE = max(0, _int("RATE_LIMIT_ADMIN_PER_MINUTE", 60))
RATE_LIMIT_JOB_PER_MINUTE = max(0, _int("RATE_LIMIT_JOB_PER_MINUTE", 30))
RATE_LIMIT_WINDOW_SECONDS = max(1, _int("RATE_LIMIT_WINDOW_SECONDS", 60))
CACHE_BACKEND = _str("CACHE_BACKEND", "memory").lower()
CACHE_REDIS_URL = _str("CACHE_REDIS_URL", "redis://localhost:6380/0")

DOMAIN_GATE_FAIL_OPEN = _bool("DOMAIN_GATE_FAIL_OPEN", False)


# --- security headers ------------------------------------------------------

SECURITY_HEADERS_ENABLED = _bool("SECURITY_HEADERS_ENABLED", True)
ENABLE_HSTS = _bool("ENABLE_HSTS", False)
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "object-src 'none'"
)
CONTENT_SECURITY_POLICY = _optional_str("CONTENT_SECURITY_POLICY") or _DEFAULT_CSP


# --- admin / scaffold wizard -----------------------------------------------

ADMIN_API_ENABLED = _bool("ADMIN_API_ENABLED", True)
ADMIN_API_LOOPBACK_ONLY = _bool("ADMIN_API_LOOPBACK_ONLY", True)

AUTO_INGEST_ON_STARTUP = _bool("AUTO_INGEST_ON_STARTUP", True)

# Post-ingest auto-generation of homepage starter questions from the
# actual ingested doc context. Fires once per pack (marker-gated) the
# first time a fresh scaffold finishes ingesting its uploaded docs.
# Replaces the generic name/label/description-only synth questions
# with 3-5 vault-grounded questions covering different intent
# archetypes (definitional / procedural / comparative / overview).
# Fallback-safe — failures swallowed, generic synth questions stay.
QUESTIONS_FROM_DOCS_ENABLED = _bool("QUESTIONS_FROM_DOCS_ENABLED", True)
# Min/max chip count produced by the doc-grounded generator. Hard
# floor 2, hard ceiling 6 — UI grid is 2-col so 4/6 fill the homepage
# cleanly (2/2 or 2/2/2 rows). Defaults to 4/6 — empty homepage area
# below the hero looked underused with the old 3/5 ceiling.
QUESTIONS_FROM_DOCS_MIN = max(2, min(6, _int("QUESTIONS_FROM_DOCS_MIN", 4)))
QUESTIONS_FROM_DOCS_MAX = max(
    QUESTIONS_FROM_DOCS_MIN, min(6, _int("QUESTIONS_FROM_DOCS_MAX", 6))
)
# Sampling budget when reading ingested source pages to build context.
QUESTIONS_FROM_DOCS_MAX_PAGES = max(1, _int("QUESTIONS_FROM_DOCS_MAX_PAGES", 8))
QUESTIONS_FROM_DOCS_MAX_CHARS_PER_PAGE = max(
    200, _int("QUESTIONS_FROM_DOCS_MAX_CHARS_PER_PAGE", 1500)
)
