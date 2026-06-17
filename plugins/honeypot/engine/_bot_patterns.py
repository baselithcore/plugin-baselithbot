"""Bot detection static patterns and thresholds."""

# Detection thresholds
HIGH_BOT_THRESHOLD = 0.70  # Confidenza forte -> BOT
LOW_BOT_THRESHOLD = 0.35  # Confidenza bassa -> HUMAN
# 0.35 < confidence < 0.70 -> PROBABLE_BOT o PROBABLE_HUMAN basato su mediana

MIN_REQUESTS_FOR_ANALYSIS = 1  # Need at least 1 request (entropy only)
MAX_TIMING_HISTORY = 50  # Keep last 50 request timestamps

# Static Patterns
BOT_USER_AGENTS = [
    r"^curl/",
    r"^wget/",
    r"^python-requests/",
    r"^python-urllib",
    r"^Go-http-client",
    r"^Java/",
    r"^libwww-perl",
    r"^Scrapy/",
    r"^httpx",
    r"^aiohttp",
    r"^axios",
    r"^node-fetch",
    r"^ruby",
    r"^PHP/",
    r"^Nikto",
    r"^Nmap",
    r"^sqlmap",
    r"^masscan",
    r"^zgrab",
    r"^Nuclei",
    r"^dirsearch",
    r"^gobuster",
    r"^ffuf",
    r"^feroxbuster",
    r"^wfuzz",
    r"^Hydra",
    r"^Medusa",
    r"^Ncrack",
    r"(?i)bot",
    r"(?i)crawler",
    r"(?i)spider",
    r"(?i)scanner",
    r"(?i)scraper",
    r"(?i)headless",
]

AUTOMATED_SCAN_PATTERNS = [
    # Path traversal fuzzing
    r"(?:\.\.[\\/]){3,}",  # Multiple path traversal
    # SQL injection fuzzing
    r"(?:union|select|insert|update|delete)\s+(?:union|select|insert|update|delete)",
    # Command injection chains
    r"[;&|]{2,}",  # Multiple command separators
    # Base64 pipeline
    r"base64.*\|\s*(?:bash|sh|python|perl)",
    # Systematic fuzzing (incremental numbers or predictable patterns)
    r"test[0-9]{3,}",
    r"user[0-9]{3,}",
    r"admin[0-9]{3,}",
    # Common scanner probes
    r"(?i)phpinfo\(",
    r"(?i)/etc/passwd",
    r"(?i)/win.ini",
    r"(?i)sleep\(\d+\)",
    r"(?i)benchmark\(",
]
