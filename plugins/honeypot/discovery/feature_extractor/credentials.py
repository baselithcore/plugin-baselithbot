"""Credential feature extraction."""

from typing import List, Set, Tuple

from ...models import AttackEvent
from .models import AttackFeatureVector

# Common default credentials for detection
DEFAULT_CREDENTIALS: Set[Tuple[str, str]] = {
    ("root", "root"),
    ("admin", "admin"),
    ("admin", "password"),
    ("root", ""),
    ("admin", "1234"),
    ("admin", "12345"),
    ("root", "123456"),
    ("user", "user"),
    ("test", "test"),
    ("guest", "guest"),
    ("admin", "admin123"),
    ("root", "toor"),
}


def extract_credential_features(
    features: AttackFeatureVector, events: List[AttackEvent]
) -> None:
    """Extract credential-related features."""
    credentials: List[Tuple[str, str]] = []
    usernames: Set[str] = set()
    default_count = 0

    for event in events:
        if event.username:
            usernames.add(event.username)
            cred = (event.username, event.password or "")
            credentials.append(cred)

            if cred in DEFAULT_CREDENTIALS:
                default_count += 1

    features.credential_attempts = len(credentials)
    features.unique_usernames = len(usernames)

    if credentials:
        features.default_cred_ratio = default_count / len(credentials)
