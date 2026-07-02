"""Wire contract for the CLI bridge surface of the control plane.

These DTOs project the framework CLI (``baselith doctor/verify/info/config``,
``db``/``cache``/``queue`` infra utilities, and the ``test``/``lint``/``docs``
dev tools) onto the dashboard. They are deliberately decoupled from the CLI's
Rich output: the backend reuses the CLI's own importable functions and
re-shapes their results here so the UI never depends on terminal formatting.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

CLI_API_VERSION = "1"


class CliCheck(BaseModel):
    """One diagnostic check projected from ``doctor``/config validation."""

    name: str
    passed: bool
    severity: str = "pass"  # pass | warn | fail
    message: str = ""
    details: str = ""


class DoctorReport(BaseModel):
    """Aggregated ``baselith doctor`` diagnostics."""

    api_version: str = CLI_API_VERSION
    available: bool = True
    error: str | None = None
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    elapsed_seconds: float = 0.0
    checks: list[CliCheck] = Field(default_factory=list)


class VerifyItem(BaseModel):
    """One row of the ``baselith verify`` installation report."""

    status: str = "pass"  # pass | warn | fail
    category: str = ""
    component: str = ""
    details: str = ""


class VerifyReport(BaseModel):
    """Aggregated ``baselith verify`` environment report."""

    api_version: str = CLI_API_VERSION
    available: bool = True
    error: str | None = None
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    elapsed_seconds: float = 0.0
    checks: list[VerifyItem] = Field(default_factory=list)


class InfoReport(BaseModel):
    """``baselith info`` framework + workspace snapshot."""

    api_version: str = CLI_API_VERSION
    available: bool = True
    error: str | None = None
    framework_version: str = ""
    python: str = ""
    os: str = ""
    project_name: str = ""
    project_detected: bool = False
    plugin_count: int = 0
    project_path: str = ""


class ConfigItem(BaseModel):
    """A single key/value pair within a configuration section."""

    key: str
    value: str


class ConfigSection(BaseModel):
    """One configuration block (core/llm/chat/vectorstore)."""

    name: str
    title: str
    available: bool = True
    error: str | None = None
    items: list[ConfigItem] = Field(default_factory=list)


class ConfigReport(BaseModel):
    """``baselith config show`` + ``validate`` projected onto the wire."""

    api_version: str = CLI_API_VERSION
    valid: bool = True
    sections: list[ConfigSection] = Field(default_factory=list)
    validation: list[CliCheck] = Field(default_factory=list)


class DbStore(BaseModel):
    """Connectivity of one persistent datastore."""

    database: str
    online: bool = False
    message: str = ""
    details: str = ""


class DbStatus(BaseModel):
    """``baselith db status`` — all persistent stores."""

    api_version: str = CLI_API_VERSION
    available: bool = True
    error: str | None = None
    stores: list[DbStore] = Field(default_factory=list)


class CacheStats(BaseModel):
    """``baselith cache stats`` — Redis memory snapshot."""

    api_version: str = CLI_API_VERSION
    ok: bool = False
    error: str | None = None
    total_keys: int | None = None
    used_memory_human: str | None = None
    peak_memory_human: str | None = None
    fragmentation_ratio: str | None = None


class QueueWorker(BaseModel):
    """One RQ worker descriptor."""

    name: str
    state: str = "unknown"


class QueueStatus(BaseModel):
    """``baselith queue status`` — RQ task-queue snapshot."""

    api_version: str = CLI_API_VERSION
    available: bool = False
    error: str | None = None
    workers: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    worker_details: list[QueueWorker] = Field(default_factory=list)


class ActionOutcome(BaseModel):
    """Outcome of a destructive infra mutation (cache clear / db reset)."""

    ok: bool = False
    message: str = ""


class JobView(BaseModel):
    """A dev-tool subprocess job (``test``/``lint``/``docs``)."""

    id: str
    kind: str  # test | lint | docs
    status: str = "running"  # running | succeeded | failed | error | timeout
    running: bool = True
    exit_code: int | None = None
    started_at: float = 0.0
    ended_at: float | None = None
    duration: float | None = None
    command: str = ""
    output: str = ""  # tail of combined stdout/stderr


__all__ = [
    "CLI_API_VERSION",
    "CliCheck",
    "DoctorReport",
    "VerifyItem",
    "VerifyReport",
    "InfoReport",
    "ConfigItem",
    "ConfigSection",
    "ConfigReport",
    "DbStore",
    "DbStatus",
    "CacheStats",
    "QueueWorker",
    "QueueStatus",
    "ActionOutcome",
    "JobView",
]
