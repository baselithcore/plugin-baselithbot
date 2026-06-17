"""Core CloudResponseGenerator class."""

import time
from typing import Any, Dict, Optional, Tuple

from ..aws_services import AWSServiceResponses
from ..generators import (
    generate_account_id,
    generate_bucket_name,
    generate_instance_id,
    generate_secret_name,
    random_string,
)
from ..templates import AWS_ERROR_TEMPLATES
from ._fake_data import FakeDataMixin
from ._api_methods import APIMethods


class CloudResponseGenerator(FakeDataMixin, APIMethods, AWSServiceResponses):
    """Generates realistic AWS-like API responses."""

    def __init__(
        self,
        account_id: Optional[str] = None,
        region: str = "us-east-1",
        organization_id: Optional[str] = None,
        imds_version: str = "v1",
    ):
        """Initialize generator with account context.

        Args:
            account_id: AWS account ID (generated if not provided)
            region: AWS region
            organization_id: AWS organization ID
            imds_version: IMDS version ("v1" or "v2")
        """
        super().__init__(
            account_id=account_id or generate_account_id(),
            region=region,
        )
        self.organization_id = organization_id or f"o-{random_string(10)}"
        self.imds_version = imds_version

        # Fake data stores (for consistency across requests)
        self._users: Dict[str, Dict] = {}
        self._roles: Dict[str, Dict] = {}
        self._buckets: Dict[str, Dict] = {}
        self._secrets: Dict[str, Dict] = {}
        self._instances: Dict[str, Dict] = {}

        # IMDSv2 token store: {token: expiry_timestamp}
        self._imds_tokens: Dict[str, float] = {}

        # Initialize with some realistic data
        self._initialize_fake_data()

    def _initialize_fake_data(self) -> None:
        """Pre-populate fake data for consistency."""
        # Create some users
        for name in ["admin", "developer", "readonly", "service-account"]:
            self._users[name] = self._create_user(name)

        # Create some roles
        for name in ["AdminRole", "LambdaExecutionRole", "EC2InstanceRole"]:
            self._roles[name] = self._create_role(name)

        # Create some buckets
        for _ in range(5):
            bucket_name = generate_bucket_name()
            self._buckets[bucket_name] = self._create_bucket(bucket_name)

        # Create some secrets
        for _ in range(3):
            secret_name = generate_secret_name()
            self._secrets[secret_name] = self._create_secret(secret_name)

        # Create some instances
        for _ in range(3):
            instance_id = generate_instance_id()
            self._instances[instance_id] = self._create_instance(instance_id)

    def _validate_imds_token(self, token: Optional[str]) -> bool:
        """Validate an IMDSv2 token.

        Args:
            token: Token to validate

        Returns:
            True if valid, False otherwise
        """
        if not token:
            return False

        expiry = self._imds_tokens.get(token)
        if not expiry:
            return False

        if time.time() > expiry:
            del self._imds_tokens[token]
            return False

        return True

    def _cleanup_expired_tokens(self) -> None:
        """Remove expired IMDSv2 tokens."""
        now = time.time()
        expired = [t for t, exp in self._imds_tokens.items() if now > exp]
        for token in expired:
            del self._imds_tokens[token]

    def error_response(self, error_code: str, **kwargs) -> Tuple[Dict, int]:
        """Generate an error response."""
        template = AWS_ERROR_TEMPLATES.get(
            error_code,
            {
                "code": error_code,
                "message": "An error occurred",
                "http_status": 400,
            },
        )

        message = template["message"].format(
            account_id=self.account_id,
            **kwargs,
        )

        return {
            "Error": {
                "Code": template["code"],
                "Message": message,
                "Type": "Sender",
            },
            "RequestId": random_string(36),
        }, template["http_status"]

    def access_denied(
        self,
        action: str,
        resource: str,
        username: str = "honeypot-user",
    ) -> Tuple[Dict, int]:
        """Generate AccessDenied error."""
        return self.error_response(
            "AccessDenied",
            action=action,
            resource=resource,
            username=username,
        )

    def handle_action(
        self,
        service: str,
        action: str,
        parameters: Dict[str, Any],
        authenticated: bool = False,
    ) -> Tuple[Dict, int]:
        """Route an API action to the appropriate response generator."""
        # Require auth for most actions
        if not authenticated and action not in ("GetCallerIdentity",):
            return self.error_response("MissingAuthenticationToken")

        # Route by service and action
        handlers = {
            # IAM
            ("iam", "GetUser"): lambda: self.get_user(parameters.get("UserName")),
            ("iam", "ListUsers"): lambda: self.list_users(
                parameters.get("MaxItems", 100)
            ),
            ("iam", "ListRoles"): lambda: self.list_roles(
                parameters.get("MaxItems", 100)
            ),
            ("iam", "CreateAccessKey"): lambda: self.create_access_key(
                parameters.get("UserName", "admin")
            ),
            # STS
            ("sts", "GetCallerIdentity"): self.get_caller_identity,
            ("sts", "AssumeRole"): lambda: self.assume_role(
                parameters.get("RoleArn", ""),
                parameters.get("RoleSessionName", "session"),
            ),
            # S3
            ("s3", "ListBuckets"): self.list_buckets,
            ("s3", "ListObjectsV2"): lambda: self.list_objects(
                parameters.get("Bucket", ""),
                parameters.get("Prefix", ""),
            ),
            ("s3", "GetObject"): lambda: self.get_object(
                parameters.get("Bucket", ""),
                parameters.get("Key", ""),
            ),
            # Secrets Manager
            ("secretsmanager", "ListSecrets"): self.list_secrets,
            ("secretsmanager", "GetSecretValue"): lambda: self.get_secret_value(
                parameters.get("SecretId", ""),
            ),
            # EC2
            ("ec2", "DescribeInstances"): self.describe_instances,
        }

        handler = handlers.get((service.lower(), action))
        if handler:
            return handler()

        # Default: access denied for unknown actions
        return self.access_denied(
            action=f"{service}:{action}",
            resource="*",
        )
