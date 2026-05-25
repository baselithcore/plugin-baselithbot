"""AWS Data Generators.

Functions for generating realistic AWS data (ARNs, IDs, names).
"""

import hashlib
import random
import string
from typing import Optional


def random_string(length: int, charset: str = None) -> str:
    """Generate random string."""
    charset = charset or (string.ascii_lowercase + string.digits)
    return "".join(random.choices(charset, k=length))


def generate_account_id() -> str:
    """Generate a realistic AWS account ID."""
    return "".join(random.choices(string.digits, k=12))


def generate_access_key_id(temp: bool = False) -> str:
    """Generate a realistic AWS access key ID."""
    prefix = "ASIA" if temp else "AKIA"
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    return f"{prefix}{suffix}"


def generate_arn(
    service: str,
    resource_type: str,
    resource_name: str,
    account_id: Optional[str] = None,
    region: str = "us-east-1",
) -> str:
    """Generate a realistic AWS ARN."""
    account = account_id or generate_account_id()
    if service in ("s3", "iam"):
        # Global services don't have region
        return f"arn:aws:{service}::{account}:{resource_type}/{resource_name}"
    return f"arn:aws:{service}:{region}:{account}:{resource_type}/{resource_name}"


def generate_instance_id() -> str:
    """Generate a realistic EC2 instance ID."""
    return f"i-{hashlib.md5(str(random.random()).encode(), usedforsecurity=False).hexdigest()[:17]}"


def generate_bucket_name() -> str:
    """Generate a realistic S3 bucket name."""
    prefixes = ["prod", "staging", "dev", "backup", "logs", "data", "assets"]
    suffixes = ["bucket", "storage", "files", "archive", "uploads"]
    prefix = random.choice(prefixes)
    suffix = random.choice(suffixes)
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}-{suffix}-{rand}"


def generate_secret_name() -> str:
    """Generate a realistic Secrets Manager secret name."""
    categories = ["prod", "staging", "dev"]
    types = ["db", "api", "oauth", "ssh", "tls", "jwt"]
    category = random.choice(categories)
    secret_type = random.choice(types)
    return f"{category}/{secret_type}/credentials"
