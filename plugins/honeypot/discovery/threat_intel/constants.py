"""Threat Intel Constants."""

EXCLUDE_IPS = {
    "127.0.0.1",
    "0.0.0.0",  # nosec B104
    "255.255.255.255",
    "10.0.0.1",
    "192.168.1.1",
    "172.16.0.1",
}

EXCLUDE_DOMAINS = {
    "localhost",
    "example.com",
    "test.com",
    "google.com",
    "microsoft.com",
    "apple.com",
}
