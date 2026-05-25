# app/config.py
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urlencode
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Carica variabili da .env
load_dotenv()


def _parse_float(value: Optional[str], default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _parse_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"false", "0", "no"}


def _parse_str_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_priority_mapping(value: Optional[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not value:
        return mapping
    for part in value.split(","):
        key, _, mapped = part.partition("=")
        key = key.strip().lower()
        mapped_value = _sanitize_str(mapped)
        if key and mapped_value:
            mapping[key] = mapped_value
    return mapping


def _sanitize_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    sanitized = value.strip()
    return sanitized or None


# === Logging ===
LOG_LEVEL_CONSOLE = os.getenv("LOG_LEVEL_CONSOLE", "INFO").upper()
# Formato log: "json" (default in prod) o "text" (legacy human-readable)
LOG_FORMAT_MODE = os.getenv("LOG_FORMAT", "text").strip().lower()
LOG_LEVEL_FILE = os.getenv("LOG_LEVEL_FILE", "INFO").upper()

# === Server FastAPI ===
# Default 0.0.0.0 perché il plugin gira tipicamente dentro un container
# Docker: bindare 127.0.0.1 lo renderebbe irraggiungibile dal reverse-proxy
# del host. Le restrizioni di rete sono compito del firewall/ingress.
HOST = os.getenv("HOST", "0.0.0.0")  # nosec B104
PORT = int(os.getenv("PORT", 8181))

# === Database ===
DATABASE_URL = _sanitize_str(os.getenv("DATABASE_URL"))
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = max(1, _parse_int(os.getenv("DB_PORT"), 5432))
DB_NAME = os.getenv("DB_NAME", "chatbot")
DB_USER = os.getenv("DB_USER", "chatbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "chatbot")
DB_SSL_MODE = _sanitize_str(os.getenv("DB_SSL_MODE"))

DB_POOL_MIN_SIZE = max(1, _parse_int(os.getenv("DB_POOL_MIN_SIZE"), 1))
DB_POOL_MAX_SIZE = max(DB_POOL_MIN_SIZE, _parse_int(os.getenv("DB_POOL_MAX_SIZE"), 5))
DB_POOL_TIMEOUT = max(0.1, _parse_float(os.getenv("DB_POOL_TIMEOUT"), 10.0))

_timezone_name = _sanitize_str(os.getenv("APP_TIMEZONE")) or "Europe/Rome"
try:
    APP_TIMEZONE = ZoneInfo(_timezone_name)
    APP_TIMEZONE_NAME = _timezone_name
except Exception:
    APP_TIMEZONE = ZoneInfo("UTC")
    APP_TIMEZONE_NAME = "UTC"


def _build_conninfo() -> str:
    """
    Produce la stringa di connessione PostgreSQL a partire dalle variabili di configurazione.

    DATABASE_URL ha precedenza assoluta; in alternativa vengono usati i singoli parametri.
    """

    if DATABASE_URL:
        return DATABASE_URL

    user = quote_plus(DB_USER or "")
    password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ""
    password_fragment = f":{password}" if password else ""
    host = DB_HOST or "localhost"
    port = DB_PORT or 5432
    query_params = {}
    if DB_SSL_MODE:
        query_params["sslmode"] = DB_SSL_MODE
    query = f"?{urlencode(query_params)}" if query_params else ""
    return f"postgresql://{user}{password_fragment}@{host}:{port}/{DB_NAME}{query}"


DB_CONNINFO = _build_conninfo()

# === Qdrant ===
QDRANT_MODE = os.getenv("QDRANT_MODE", "embedded").lower()  # "embedded" | "server"
QDRANT_PATH = Path(os.getenv("QDRANT_PATH", "./qdrant_data"))
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("COLLECTION_NAME", "filesystem_bot")

# === GraphDB (FalkorDB/RedisGraph compatibile) ===
GRAPH_DB_ENABLED = _parse_bool(os.getenv("GRAPH_DB_ENABLED"), True)
GRAPH_DB_URL = os.getenv("GRAPH_DB_URL", "redis://localhost:6379")
GRAPH_DB_NAME = os.getenv("GRAPH_DB_NAME", "agent_graph")
GRAPH_DB_TIMEOUT = max(0.1, _parse_float(os.getenv("GRAPH_DB_TIMEOUT"), 2.0))
GRAPH_DB_CREATE_CONSTRAINTS = _parse_bool(
    os.getenv("GRAPH_DB_CREATE_CONSTRAINTS"), False
)
GRAPH_SIMILAR_TOP_K = max(1, _parse_int(os.getenv("GRAPH_SIMILAR_TOP_K"), 5))
GRAPH_RAG_ENABLED = _parse_bool(os.getenv("GRAPH_RAG_ENABLED"), False)

# === Chat retrieval tuning ===
CHAT_INITIAL_SEARCH_K = max(1, _parse_int(os.getenv("CHAT_INITIAL_SEARCH_K"), 50))
CHAT_FINAL_TOP_K = max(1, _parse_int(os.getenv("CHAT_FINAL_TOP_K"), 5))
CHAT_RERANK_THRESHOLD = _parse_float(os.getenv("CHAT_RERANK_THRESHOLD"), 0.0)
RERANK_MAX_CANDIDATES = max(
    1, _parse_int(os.getenv("RERANK_MAX_CANDIDATES"), CHAT_INITIAL_SEARCH_K)
)

# === Indicizzazione / bootstrap ===
INDEX_BOOTSTRAP_ENABLED = _parse_bool(os.getenv("INDEX_BOOTSTRAP_ENABLED"), True)
_bootstrap_sentinel = (
    _sanitize_str(os.getenv("INDEX_BOOTSTRAP_SENTINEL")) or "data/.index_bootstrap"
)
INDEX_BOOTSTRAP_SENTINEL = Path(_bootstrap_sentinel).expanduser()
if not INDEX_BOOTSTRAP_SENTINEL.is_absolute():
    INDEX_BOOTSTRAP_SENTINEL = Path.cwd() / INDEX_BOOTSTRAP_SENTINEL

INDEX_BOOTSTRAP_BACKGROUND = _parse_bool(os.getenv("INDEX_BOOTSTRAP_BACKGROUND"), False)

INDEX_STATE_PATH = Path(
    _sanitize_str(os.getenv("INDEX_STATE_PATH")) or "data/index_state.json"
).expanduser()
if not INDEX_STATE_PATH.is_absolute():
    INDEX_STATE_PATH = Path.cwd() / INDEX_STATE_PATH

INDEX_EMBED_BATCH_SIZE = max(8, _parse_int(os.getenv("INDEX_EMBED_BATCH_SIZE"), 32))
INDEX_QDRANT_WAIT = _parse_bool(os.getenv("INDEX_QDRANT_WAIT"), False)


# === Client Qdrant (switch dinamico) ===
if QDRANT_MODE == "server":
    print(f"[config] ✅ Qdrant in modalità SERVER → {QDRANT_URL}", file=sys.stderr)
    QDRANT = QdrantClient(url=QDRANT_URL)
else:
    QDRANT_PATH.mkdir(parents=True, exist_ok=True)
    print(f"[config] ✅ Qdrant in modalità EMBEDDED → {QDRANT_PATH}", file=sys.stderr)
    QDRANT = QdrantClient(path=str(QDRANT_PATH))

if GRAPH_DB_ENABLED:
    print(
        f"[config] ✅ GraphDB abilitato → {GRAPH_DB_URL} (grafico: {GRAPH_DB_NAME})",
        file=sys.stderr,
    )
else:
    print("[config] ℹ️ GraphDB disabilitato (GRAPH_DB_ENABLED=false)", file=sys.stderr)

# === Modelli (solo nomi, non istanze) ===
EMBEDDER_MODEL = os.getenv("EMBEDDER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

# === OpenAI ===
OPENAI_ENABLED = _parse_bool(os.getenv("OPENAI"), False)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# === Feedback ===
_DEFAULT_ENABLE_FEEDBACK = _parse_bool(os.getenv("ENABLE_FEEDBACK"), True)
POSTGRES_ENABLED = _parse_bool(
    os.getenv("POSTGRES_ENABLED"),
    _DEFAULT_ENABLE_FEEDBACK,
)
ENABLE_FEEDBACK = POSTGRES_ENABLED and _DEFAULT_ENABLE_FEEDBACK
FEEDBACK_BOOST_ENABLED = POSTGRES_ENABLED and _parse_bool(
    os.getenv("FEEDBACK_BOOST_ENABLED"), True
)
FEEDBACK_POSITIVE_WEIGHT = _parse_float(os.getenv("FEEDBACK_POSITIVE_WEIGHT"), 0.05)
FEEDBACK_NEGATIVE_WEIGHT = _parse_float(os.getenv("FEEDBACK_NEGATIVE_WEIGHT"), 0.1)
FEEDBACK_SCORE_MIN_TOTAL = max(0, _parse_int(os.getenv("FEEDBACK_SCORE_MIN_TOTAL"), 3))

ACTIVE_LEARNING_MIN_TOTAL = max(
    1, _parse_int(os.getenv("ACTIVE_LEARNING_MIN_TOTAL"), 4)
)
ACTIVE_LEARNING_MAX_POSITIVE_RATE = max(
    0.0,
    min(
        1.0,
        _parse_float(os.getenv("ACTIVE_LEARNING_MAX_POSITIVE_RATE"), 0.6),
    ),
)
ACTIVE_LEARNING_LIMIT = max(1, _parse_int(os.getenv("ACTIVE_LEARNING_LIMIT"), 20))

# === Chatbot widget ===
CHATBOT_COLOR_ENV_KEYS = (
    "CHATBOT_PRIMARY_COLOR",
    "CHATBOT_PRIMARY_TEXT_COLOR",
    "CHATBOT_WINDOW_BACKGROUND_COLOR",
    "CHATBOT_MESSAGES_BACKGROUND_COLOR",
    "CHATBOT_BORDER_COLOR",
    "CHATBOT_USER_MESSAGE_BACKGROUND_COLOR",
    "CHATBOT_USER_MESSAGE_TEXT_COLOR",
    "CHATBOT_BOT_MESSAGE_BACKGROUND_COLOR",
    "CHATBOT_BOT_MESSAGE_TEXT_COLOR",
    "CHATBOT_TYPING_INDICATOR_COLOR",
    "CHATBOT_FEEDBACK_POSITIVE_COLOR",
    "CHATBOT_FEEDBACK_NEGATIVE_COLOR",
)

CHATBOT_COLOR_OVERRIDES = {
    key: value
    for key in CHATBOT_COLOR_ENV_KEYS
    for value in [_sanitize_str(os.getenv(key))]
    if value is not None
}

CHATBOT_API_URL = _sanitize_str(os.getenv("CHATBOT_API_URL"))
CHATBOT_ENABLE_FEEDBACK = _parse_bool(
    os.getenv("CHATBOT_ENABLE_FEEDBACK"), ENABLE_FEEDBACK
)

CHATBOT_CLIENT_CONFIG = {
    "api_url": CHATBOT_API_URL,
    "feedback_enabled": CHATBOT_ENABLE_FEEDBACK,
    "color_overrides": CHATBOT_COLOR_OVERRIDES,
}

# === Cache ===
CHAT_RESPONSE_CACHE_ENABLED = _parse_bool(
    os.getenv("CHAT_RESPONSE_CACHE_ENABLED"), True
)
CHAT_RESPONSE_CACHE_TTL = _parse_float(
    os.getenv("CHAT_RESPONSE_CACHE_TTL") or os.getenv("LLM_CACHE_TTL"), 3600.0
)
CHAT_RESPONSE_CACHE_MAXSIZE = max(
    1, _parse_int(os.getenv("CHAT_RESPONSE_CACHE_MAXSIZE"), 256)
)

CHAT_RERANK_CACHE_ENABLED = _parse_bool(os.getenv("CHAT_RERANK_CACHE_ENABLED"), True)
CHAT_RERANK_CACHE_TTL = _parse_float(os.getenv("CHAT_RERANK_CACHE_TTL"), 600.0)
CHAT_RERANK_CACHE_MAXSIZE = max(
    1, _parse_int(os.getenv("CHAT_RERANK_CACHE_MAXSIZE"), 4096)
)

ANALYSIS_CACHE_ENABLED = _parse_bool(os.getenv("ANALYSIS_CACHE_ENABLED"), True)
ANALYSIS_CACHE_TTL = _parse_float(os.getenv("ANALYSIS_CACHE_TTL"), 86400.0)
ANALYSIS_CACHE_MAXSIZE = max(1, _parse_int(os.getenv("ANALYSIS_CACHE_MAXSIZE"), 128))

CACHE_BACKEND = (_sanitize_str(os.getenv("CACHE_BACKEND")) or "local").lower()
if CACHE_BACKEND not in {"local", "redis"}:
    CACHE_BACKEND = "local"
CACHE_REDIS_URL = (
    _sanitize_str(os.getenv("CACHE_REDIS_URL")) or "redis://localhost:6379/0"
)
CACHE_REDIS_PREFIX = _sanitize_str(os.getenv("CACHE_REDIS_PREFIX")) or "agentbot"

CHAT_MEMORY_ENABLED = _parse_bool(os.getenv("CHAT_MEMORY_ENABLED"), True)
CHAT_MEMORY_TTL = _parse_float(os.getenv("CHAT_MEMORY_TTL"), 3600.0)
CHAT_MEMORY_MAX_TURNS = max(1, _parse_int(os.getenv("CHAT_MEMORY_MAX_TURNS"), 6))
CHAT_MEMORY_MAX_SESSIONS = max(
    1, _parse_int(os.getenv("CHAT_MEMORY_MAX_SESSIONS"), 1024)
)
CHAT_MEMORY_SUMMARY_ENABLED = _parse_bool(
    os.getenv("CHAT_MEMORY_SUMMARY_ENABLED"), True
)
CHAT_MEMORY_SUMMARY_MAX_TURNS = max(
    0, _parse_int(os.getenv("CHAT_MEMORY_SUMMARY_MAX_TURNS"), 8)
)
CHAT_MEMORY_SUMMARY_MAX_CHARS = max(
    120, _parse_int(os.getenv("CHAT_MEMORY_SUMMARY_MAX_CHARS"), 800)
)

# === Chat Streaming ===
CHAT_STREAMING_ENABLED = _parse_bool(os.getenv("CHAT_STREAMING_ENABLED"), True)

# === Admin ===
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")
ADMIN_PASS_HASHED = _sanitize_str(os.getenv("ADMIN_PASS_HASHED"))

# === Sicurezza / Auth ===
ALLOW_ORIGINS = _parse_str_list(os.getenv("ALLOW_ORIGINS")) or ["*"]
AUTH_REQUIRED = _parse_bool(os.getenv("AUTH_REQUIRED"), False)

# === Multi-Tenancy ===
MULTI_TENANT_ENABLED = _parse_bool(os.getenv("MULTI_TENANT_ENABLED"), False)
MULTI_TENANT_REQUIRED = _parse_bool(os.getenv("MULTI_TENANT_REQUIRED"), False)

# Quota utenti per piano tenant.
# Modello SaaS: ogni tenant è uno spazio personale con un solo proprietario.
# La quota è configurabile per piano per consentire evoluzioni future,
# ma tutti i piani attuali ammettono 1 solo utente.
PLAN_MAX_USERS: Dict[str, int] = {
    "free": 1,
    "pro": 1,
    "business": 1,
    "enterprise": 1,
}
API_KEYS_USER = set(_parse_str_list(os.getenv("API_KEYS_USER")))
API_KEYS_ADMIN = set(_parse_str_list(os.getenv("API_KEYS_ADMIN")))
API_KEYS_JOB = set(_parse_str_list(os.getenv("API_KEYS_JOB")))
SECRET_KEY = _sanitize_str(os.getenv("SECRET_KEY"))

RATE_LIMIT_USER_PER_MINUTE = _parse_optional_int(
    os.getenv("RATE_LIMIT_USER_PER_MINUTE")
)
RATE_LIMIT_ADMIN_PER_MINUTE = _parse_optional_int(
    os.getenv("RATE_LIMIT_ADMIN_PER_MINUTE")
)
RATE_LIMIT_JOB_PER_MINUTE = _parse_optional_int(os.getenv("RATE_LIMIT_JOB_PER_MINUTE"))
RATE_LIMIT_WINDOW_SECONDS = max(
    1, _parse_int(os.getenv("RATE_LIMIT_WINDOW_SECONDS"), 60)
)

SECURITY_HEADERS_ENABLED = _parse_bool(os.getenv("SECURITY_HEADERS_ENABLED"), True)
CONTENT_SECURITY_POLICY = _sanitize_str(os.getenv("CONTENT_SECURITY_POLICY"))
ENABLE_HSTS = _parse_bool(os.getenv("ENABLE_HSTS"), False)

# Upload: dimensione massima file in bytes (default 50 MB)
MAX_UPLOAD_SIZE_BYTES = _parse_int(os.getenv("MAX_UPLOAD_SIZE_BYTES"), 50 * 1024 * 1024)

DOCUMENTS_ROOT = Path(os.getenv("DOCUMENTS_PATH", "documents")).expanduser()
if not DOCUMENTS_ROOT.is_absolute():
    DOCUMENTS_ROOT = Path.cwd() / DOCUMENTS_ROOT
DOCUMENTS_ROOT.mkdir(parents=True, exist_ok=True)

DEFAULT_DOCUMENT_EXTENSIONS = (
    ".md",
    ".markdown",
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".tif",
    ".tiff",
)

_document_extensions = _parse_str_list(os.getenv("DOCUMENTS_EXTENSIONS"))
if _document_extensions:
    DOCUMENTS_EXTENSIONS = tuple(
        ext if ext.startswith(".") else f".{ext}" for ext in _document_extensions
    )
else:
    DOCUMENTS_EXTENSIONS = DEFAULT_DOCUMENT_EXTENSIONS

# === Web crawling / siti esterni ===
WEB_DOCUMENTS_ENABLED = _parse_bool(
    os.getenv("WEB_DOCUMENTS_ENABLED"),
    False,
)
WEB_DOCUMENTS_URLS = _parse_str_list(os.getenv("WEB_DOCUMENTS_URLS"))
WEB_DOCUMENTS_MAX_PAGES = max(
    1,
    _parse_int(os.getenv("WEB_DOCUMENTS_MAX_PAGES"), 5),
)
WEB_DOCUMENTS_MAX_DEPTH = max(
    1,
    _parse_int(os.getenv("WEB_DOCUMENTS_MAX_DEPTH"), 2),
)
WEB_DOCUMENTS_RENDER_TIMEOUT = max(
    1.0,
    _parse_float(os.getenv("WEB_DOCUMENTS_RENDER_TIMEOUT"), 20.0),
)
WEB_DOCUMENTS_WAIT_SELECTOR = _sanitize_str(os.getenv("WEB_DOCUMENTS_WAIT_SELECTOR"))
WEB_DOCUMENTS_USER_AGENT = _sanitize_str(os.getenv("WEB_DOCUMENTS_USER_AGENT")) or (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
WEB_DOCUMENTS_ALLOWLIST = _parse_str_list(os.getenv("WEB_DOCUMENTS_ALLOWLIST"))
# === spaCy / NLP ===
ENABLE_SPACY_DOCUMENTS = _parse_bool(os.getenv("ENABLE_SPACY_DOCUMENTS"), True)
SPACY_MODEL = _sanitize_str(os.getenv("SPACY_MODEL")) or "it_core_news_md"
SPACY_FALLBACK_LANGUAGE = _sanitize_str(os.getenv("SPACY_FALLBACK_LANGUAGE"))

# === OCR ===
_raw_easyocr_langs = _sanitize_str(os.getenv("EASYOCR_LANGUAGES")) or "it,en"
EASYOCR_LANGUAGES: list[str] = [
    lang.strip() for lang in _raw_easyocr_langs.split(",") if lang.strip()
]
EASYOCR_USE_GPU = _parse_bool(os.getenv("EASYOCR_USE_GPU"), False)

# === Guardrails / Intent ===
CHAT_GUARDRAILS_ENABLED = _parse_bool(os.getenv("CHAT_GUARDRAILS_ENABLED"), True)
CHAT_GUARDRAILS_BLOCK_MESSAGE = (
    _sanitize_str(os.getenv("CHAT_GUARDRAILS_BLOCK_MESSAGE"))
    or "Non posso assisterti su questa richiesta."
)
CHAT_GUARDRAILS_OUT_OF_SCOPE_MESSAGE = _sanitize_str(
    os.getenv("CHAT_GUARDRAILS_OUT_OF_SCOPE_MESSAGE")
) or (
    "Posso rispondere solo a domande legate ai documenti indicizzati. "
    "Prova a fornire riferimenti piu specifici."
)
CHAT_GUARDRAILS_BLOCK_KEYWORDS = _parse_str_list(
    os.getenv("CHAT_GUARDRAILS_BLOCK_KEYWORDS")
)
CHAT_GUARDRAILS_OUT_OF_SCOPE_PATTERNS = _parse_str_list(
    os.getenv("CHAT_GUARDRAILS_OUT_OF_SCOPE_PATTERNS")
)

# === Agile Project Manager / Jira ===
ENABLE_PROJECT_MANAGER_MODE = _parse_bool(
    os.getenv("ENABLE_PROJECT_MANAGER_MODE"), True
)
CONSOLE_CHAT_ENABLED = _parse_bool(os.getenv("CONSOLE_CHAT_ENABLED"), True)
CONSOLE_ANALYSIS_ENABLED = _parse_bool(
    os.getenv("CONSOLE_ANALYSIS_ENABLED"), ENABLE_PROJECT_MANAGER_MODE
)
PROJECT_PLANNER_MAX_STORIES = max(
    1, _parse_int(os.getenv("PROJECT_PLANNER_MAX_STORIES"), 10)
)
PROJECT_PLANNER_ENABLE_TEST_CASES = _parse_bool(
    os.getenv("PROJECT_PLANNER_ENABLE_TEST_CASES"), True
)
PROJECT_PLANNER_MAX_TEST_CASES = max(
    1, _parse_int(os.getenv("PROJECT_PLANNER_MAX_TEST_CASES"), 2)
)
PROJECT_PLANNER_MIN_SCENARIOS = max(
    1, _parse_int(os.getenv("PROJECT_PLANNER_MIN_SCENARIOS"), 1)
)

ENABLE_JIRA_AUTOMATION = _parse_bool(os.getenv("ENABLE_JIRA_AUTOMATION"), False)
JIRA_REQUIRE_MANUAL_APPROVAL = _parse_bool(
    os.getenv("JIRA_REQUIRE_MANUAL_APPROVAL"), False
)
JIRA_BASE_URL = _sanitize_str(os.getenv("JIRA_BASE_URL"))
JIRA_EMAIL = _sanitize_str(os.getenv("JIRA_EMAIL"))
JIRA_API_TOKEN = _sanitize_str(os.getenv("JIRA_API_TOKEN"))
JIRA_PROJECT_KEY = _sanitize_str(os.getenv("JIRA_PROJECT_KEY"))
JIRA_ISSUE_TYPE = _sanitize_str(os.getenv("JIRA_ISSUE_TYPE")) or "Story"
JIRA_TESTCASE_ISSUE_TYPE = (
    _sanitize_str(os.getenv("JIRA_TESTCASE_ISSUE_TYPE")) or "Test Case"
)
JIRA_DEFAULT_LABELS = _parse_str_list(os.getenv("JIRA_DEFAULT_LABELS"))
JIRA_STORY_POINTS_FIELD = _sanitize_str(os.getenv("JIRA_STORY_POINTS_FIELD"))
JIRA_KB_LABEL_FIELD = _sanitize_str(os.getenv("JIRA_KB_LABEL_FIELD"))
JIRA_REQUEST_TIMEOUT = max(1.0, _parse_float(os.getenv("JIRA_REQUEST_TIMEOUT"), 15.0))
JIRA_DEFAULT_PRIORITY_NAME = (
    _sanitize_str(os.getenv("JIRA_DEFAULT_PRIORITY_NAME")) or "Medium"
)
_DEFAULT_JIRA_PRIORITY_MAPPING = {
    "must": "High",
    "should": "Medium",
    "could": "Low",
}
JIRA_PRIORITY_MAPPING = _DEFAULT_JIRA_PRIORITY_MAPPING.copy()
# === Audit Agent ===
AUDIT_ENABLED = _parse_bool(os.getenv("AUDIT_ENABLED"), False)
AUDIT_BLOCK_ON_RISK = _parse_bool(os.getenv("AUDIT_BLOCK_ON_RISK"), False)

# === Cost Control / Budgeting ===
# Limiti obbligatori per Phase 1 Cost Optimization
COST_CONTROL_ENABLED = _parse_bool(os.getenv("COST_CONTROL_ENABLED"), True)
AGENT_MAX_TOKENS = max(100, _parse_int(os.getenv("AGENT_MAX_TOKENS"), 10000))
GRAPH_QUERY_LIMIT = max(1, _parse_int(os.getenv("GRAPH_QUERY_LIMIT"), 30))
GRAPH_MAX_HOPS = max(1, _parse_int(os.getenv("GRAPH_MAX_HOPS"), 3))
GRAPH_QUERY_TIMEOUT = max(0.1, _parse_float(os.getenv("GRAPH_QUERY_TIMEOUT"), 5.0))

# Cost Control - Phase 2 (Caching)
GRAPH_CACHE_TTL = max(
    1.0, _parse_float(os.environ.get("GRAPH_CACHE_TTL"), 600.0)
)  # 10 min
EMBEDDING_CACHE_TTL = max(
    1.0, _parse_float(os.environ.get("EMBEDDING_CACHE_TTL"), 86400.0)
)  # 24h
LLM_CACHE_TTL = max(1.0, _parse_float(os.environ.get("LLM_CACHE_TTL"), 3600.0))  # 1h
