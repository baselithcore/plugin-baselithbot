from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Plugin-port note: extra="ignore" tolerates host-process env vars (CORE_*,
    # other plugins' DOCHECK_-unrelated keys). The original docheck-engine ran
    # standalone with its own .env so this knob was unnecessary; under
    # BaselithCore the .env at repo root is shared across plugins.
    model_config = SettingsConfigDict(
        env_prefix="DOCHECK_", env_file=".env", extra="ignore"
    )

    app_name: str = "docheck-engine"
    version: str = "0.1.0"
    debug: bool = False

    storage_root: Path = Path("./storage")
    db_path: Path = Path("./storage/docheck.db")
    db_key_keyring_service: str = "docheck"
    db_key_keyring_user: str = "master"
    db_encryption_enabled: bool = False  # F4 hardening: True + extra [encryption]

    socket_path: Path = Path("./storage/docheck.sock")
    bind_tcp: str | None = None  # "127.0.0.1:8765" only when explicitly enabled

    # LLM
    # Provider: ollama (default, local), vllm, openai-compatible
    llm_provider: str = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "ollama"  # placeholder; ignored by local servers
    llm_primary_model: str = "llama3.1:8b"
    llm_fallback_model: str = "qwen2.5:3b"
    llm_temperature: float = 0.1
    llm_top_p: float = 0.9
    llm_request_timeout_s: float = 120.0

    # Embedding
    embedding_model: str = "BAAI/bge-m3"

    # Vector DB
    chroma_persist_dir: Path = Path("./storage/chroma")

    # OCR
    ocr_engine: str = "paddleocr"

    # Audit
    audit_signing_key_path: Path = Path("./storage/audit_ed25519.key")

    # Retention
    retention_default_days: int = 365

    # Multi-tenant (post-MVP — disabled by default).
    #
    # Single-tenant locale (default): SQLite + Chroma embedded → zero
    # dipendenze esterne, ``./storage/*`` self-contained.
    # Multi-tenant produzione: si appoggia allo stack root
    # ``baselithcore-enterprise`` — Postgres condiviso (``postgres_db``)
    # + Qdrant condiviso (``baselith-core-qdrant``). Il plugin riusa le
    # istanze esistenti con suddivisione logica via DB/collection
    # dedicata, nessun container nuovo. Override con:
    #   DOCHECK_DB_BACKEND=postgres
    #   DOCHECK_POSTGRES_DSN=postgresql+asyncpg://docheck:dev@localhost:5432/docheck
    #   DOCHECK_VECTOR_BACKEND=qdrant
    #   DOCHECK_QDRANT_URL=http://localhost:6333
    multitenant_enabled: bool = False
    db_backend: str = "sqlite"  # sqlite | postgres
    postgres_dsn: str = ""  # postgresql+asyncpg://docheck:dev@localhost:5432/docheck
    vector_backend: str = "chroma"  # chroma | qdrant
    qdrant_url: str = ""  # http://localhost:6333 (root stack)

    # OIDC (activated when issuer set)
    oidc_issuer: str = ""
    oidc_audience: str = "docheck"
    oidc_jwks_uri: str = ""

    # DocCheck_Builtin policy controls (deterministic baseline rules).
    # Comma-separated rule ids to disable, e.g. "FORMAT-DATE-ISO,ID-CF-CHECKSUM".
    builtin_disabled_rules: str = ""
    # Severity overrides, format "RULE_ID=FAIL,RULE_ID2=WARN".
    builtin_severity_overrides: str = ""

    @property
    def docs_dir(self) -> Path:
        return self.storage_root / "docs"


settings = Settings()
