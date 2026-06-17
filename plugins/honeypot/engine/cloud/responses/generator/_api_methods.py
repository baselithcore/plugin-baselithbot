"""Public API methods mixin for CloudResponseGenerator."""

import hashlib
import json
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from ..generators import generate_instance_id, random_string
from ._console_html import render_console_login_page


class APIMethods:
    """Mixin providing the 13 public API methods."""

    def get_user(self, username: Optional[str] = None) -> Tuple[Dict, int]:
        """Generate GetUser response."""
        if username and username in self._users:
            return self.iam_get_user(username, self._users[username])

        if username:
            return self.error_response(
                "NoSuchEntity", entity_type="user", entity_name=username
            )

        # Return current user (caller identity)
        return self.iam_get_user(
            "admin", self._users.get("admin", self._create_user("admin"))
        )

    def list_users(self, max_items: int = 100) -> Tuple[Dict, int]:
        """Generate ListUsers response."""
        return self.iam_list_users(list(self._users.values()), max_items)

    def list_roles(self, max_items: int = 100) -> Tuple[Dict, int]:
        """Generate ListRoles response."""
        return self.iam_list_roles(list(self._roles.values()), max_items)

    def get_caller_identity(self) -> Tuple[Dict, int]:
        """Generate GetCallerIdentity response (STS)."""
        return self.sts_get_caller_identity()

    def create_access_key(self, username: str) -> Tuple[Dict, int]:
        """Generate CreateAccessKey response - BAIT."""
        return self.iam_create_access_key(username)

    def list_buckets(self) -> Tuple[Dict, int]:
        """Generate ListBuckets response."""
        return self.s3_list_buckets(self._buckets)

    def list_objects(self, bucket: str, prefix: str = "") -> Tuple[Dict, int]:
        """Generate ListObjectsV2 response."""
        if bucket not in self._buckets:
            return self.error_response("NoSuchBucket")
        return self.s3_list_objects(bucket, prefix)

    def get_object(self, bucket: str, key: str) -> Tuple[Dict, int]:
        """Generate GetObject response - BAIT."""
        if bucket not in self._buckets:
            return self.error_response("NoSuchBucket")
        return self.s3_get_object(bucket, key)

    def list_secrets(self) -> Tuple[Dict, int]:
        """Generate ListSecrets response."""
        return self.secrets_list_secrets(self._secrets)

    def get_secret_value(self, secret_id: str) -> Tuple[Dict, int]:
        """Generate GetSecretValue response - BAIT."""
        # Find secret by ARN or name
        secret = None
        for name, data in self._secrets.items():
            if secret_id in (data["ARN"], data["Name"], name):
                secret = data
                break

        if not secret:
            return self.error_response("ResourceNotFoundException")

        return self.secrets_get_secret_value(secret)

    def describe_instances(self) -> Tuple[Dict, int]:
        """Generate DescribeInstances response."""
        return self.ec2_describe_instances(self._instances)

    def assume_role(self, role_arn: str, session_name: str) -> Tuple[Dict, int]:
        """Generate AssumeRole response - BAIT."""
        return self.sts_assume_role(role_arn, session_name)

    def imds_metadata(
        self,
        path: str,
        token: Optional[str] = None,
    ) -> Tuple[Any, int]:
        """Generate IMDS metadata response.

        Args:
            path: Metadata path requested
            token: IMDSv2 token (required if imds_version is "v2")

        Returns:
            Tuple of (response_body, http_status)
        """
        # IMDSv2 token validation
        if self.imds_version == "v2" and not self._validate_imds_token(token):
            return {"message": "Unauthorized"}, 401

        # Build region-aware metadata
        instance_id = (
            list(self._instances.keys())[0]
            if self._instances
            else generate_instance_id()
        )
        az = f"{self.region}a"  # e.g., eu-south-1a
        hostname = f"ip-10-0-1-50.{self.region}.compute.internal"

        metadata_map = {
            # Directory listings
            "/latest/meta-data/": "ami-id\nami-launch-index\nhostname\ninstance-id\ninstance-type\nlocal-hostname\nlocal-ipv4\nmac\nnetwork/\nplacement/\npublic-hostname\npublic-ipv4\niam/\nservices/",
            "/latest/meta-data/placement/": "availability-zone\navailability-zone-id\nregion",
            "/latest/meta-data/network/": "interfaces/",
            "/latest/meta-data/iam/": "info\nsecurity-credentials/",
            # Instance identity
            "/latest/meta-data/instance-id": instance_id,
            "/latest/meta-data/instance-type": "t3.medium",
            "/latest/meta-data/ami-id": f"ami-{random_string(8)}",
            "/latest/meta-data/ami-launch-index": "0",
            # Networking
            "/latest/meta-data/local-ipv4": "10.0.1.50",
            "/latest/meta-data/local-hostname": hostname,
            "/latest/meta-data/public-ipv4": f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "/latest/meta-data/public-hostname": f"ec2-{random.randint(1, 255)}-{random.randint(0, 255)}-{random.randint(0, 255)}-{random.randint(1, 254)}.{self.region}.compute.amazonaws.com",
            "/latest/meta-data/hostname": hostname,
            "/latest/meta-data/mac": "0a:1b:2c:3d:4e:5f",
            # Placement (region-aware)
            "/latest/meta-data/placement/availability-zone": az,
            "/latest/meta-data/placement/availability-zone-id": f"{self.region}-az1",
            "/latest/meta-data/placement/region": self.region,
            # IAM
            "/latest/meta-data/iam/info": json.dumps(
                {
                    "Code": "Success",
                    "LastUpdated": datetime.now(timezone.utc).isoformat() + "Z",
                    "InstanceProfileArn": f"arn:aws:iam::{self.account_id}:instance-profile/honeypot-profile",
                    "InstanceProfileId": f"AIPA{random_string(17)}",
                }
            ),
            "/latest/meta-data/iam/security-credentials/": "honeypot-role",
            # Services
            "/latest/meta-data/services/domain": "amazonaws.com",
            "/latest/meta-data/services/partition": "aws",
            # User data (enticing bait)
            "/latest/user-data": f"""#!/bin/bash
# Bootstrap script for {self.region}
export AWS_DEFAULT_REGION={self.region}
export DB_HOST=db.internal.company.local
export DB_PASSWORD=Pr0dP@ss_2024!
aws s3 cp s3://company-configs/app.env /etc/app.env
""",
            # Dynamic data
            "/latest/dynamic/instance-identity/document": json.dumps(
                {
                    "accountId": self.account_id,
                    "architecture": "x86_64",
                    "availabilityZone": az,
                    "imageId": f"ami-{random_string(8)}",
                    "instanceId": instance_id,
                    "instanceType": "t3.medium",
                    "kernelId": None,
                    "pendingTime": (
                        datetime.now(timezone.utc)
                        - timedelta(hours=random.randint(1, 720))
                    ).isoformat()
                    + "Z",
                    "privateIp": "10.0.1.50",
                    "ramdiskId": None,
                    "region": self.region,
                    "version": "2017-09-30",
                }
            ),
        }

        if path in metadata_map:
            return metadata_map[path], 200
        if path.startswith("/latest/meta-data/iam/security-credentials/"):
            role_name = path.split("/")[-1]
            return self.imds_security_credentials(role_name)

        return "Not Found", 404

    def imds_put_token(self, ttl_seconds: int = 21600) -> Tuple[str, int]:
        """Generate IMDSv2 token (PUT /latest/api/token).

        Args:
            ttl_seconds: Token TTL in seconds (max 21600 = 6 hours)

        Returns:
            Tuple of (token, http_status)
        """
        # Validate TTL (AWS limits: 1-21600 seconds)
        ttl_seconds = max(1, min(21600, ttl_seconds))

        # Generate token
        token = hashlib.sha256(
            f"{time.time()}-{random_string(16)}".encode()
        ).hexdigest()

        # Store with expiry
        expiry = time.time() + ttl_seconds
        self._imds_tokens[token] = expiry

        # Cleanup expired tokens
        self._cleanup_expired_tokens()

        return token, 200

    def get_console_login_page(
        self, csrf_token: Optional[str] = None
    ) -> Tuple[str, int]:
        """Generate fake AWS Console login page.

        Returns:
            Tuple of (html_content, http_status)
        """
        token = csrf_token or random_string(32)
        html = render_console_login_page(token)
        return html, 200
