"""Cloud Response Generation Module.

Generates realistic AWS-like API responses with version-specific error messages
and bait content.
"""

from .generator import CloudResponseGenerator
from .generators import (
    generate_access_key_id,
    generate_account_id,
    generate_arn,
    generate_bucket_name,
    generate_instance_id,
    generate_secret_name,
    random_string,
)
from .templates import AWS_ERROR_TEMPLATES

__all__ = [
    # Main generator
    "CloudResponseGenerator",
    # Data generators
    "generate_account_id",
    "generate_access_key_id",
    "generate_arn",
    "generate_instance_id",
    "generate_bucket_name",
    "generate_secret_name",
    "random_string",
    # Templates
    "AWS_ERROR_TEMPLATES",
]
