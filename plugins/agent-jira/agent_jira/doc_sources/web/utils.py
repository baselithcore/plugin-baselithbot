import re
from urllib.parse import urlparse

from agent_jira.config import WEB_DOCUMENTS_ALLOWLIST

BINARY_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".zip",
    ".pdf",
    ".rar",
    ".tar",
    ".gz",
    ".tgz",
    ".mp3",
    ".mp4",
    ".mov",
    ".ppt",
    ".pptx",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

PRIVATE_IP_PREFIXES = (
    "10.",
    "127.",
    "169.254.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
)


def normalize_domain(domain: str) -> str:
    return domain.lower().lstrip("www.")


def normalize_parsed(parsed) -> str:
    path = parsed.path or "/"
    normalized_path = path if path.startswith("/") else f"/{path}"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://{parsed.netloc}{normalized_path}{query}"


def normalize_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    trimmed = raw_url.strip()
    if not trimmed:
        return None
    if "://" not in trimmed:
        trimmed = f"https://{trimmed}"
    parsed = urlparse(trimmed)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return normalize_parsed(parsed)


def should_skip_url(url: str) -> bool:
    parsed = urlparse(url)
    extension = ""
    if "." in parsed.path.rsplit("/", 1)[-1]:
        _, _, candidate = parsed.path.rpartition(".")
        extension = f".{candidate.lower()}"
    if extension in BINARY_EXTENSIONS:
        return True

    hostname = parsed.hostname or ""
    # Blocca IP privati/loopback/link-local
    if any(hostname.startswith(prefix) for prefix in PRIVATE_IP_PREFIXES):
        return True
    # Blocca porte non standard
    if parsed.port and parsed.port not in {80, 443}:
        return True

    # Allowlist domini se configurata
    if WEB_DOCUMENTS_ALLOWLIST:
        domain = normalize_domain(hostname)
        allowed = {normalize_domain(d) for d in WEB_DOCUMENTS_ALLOWLIST}
        return domain not in allowed

    return False


def get_document_id(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    normalized_path = path if path.startswith("/") else f"/{path}"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.netloc}{normalized_path}{query}"


def clean_block(text: str, min_chars: int) -> str | None:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) < min_chars:
        return None
    return cleaned
