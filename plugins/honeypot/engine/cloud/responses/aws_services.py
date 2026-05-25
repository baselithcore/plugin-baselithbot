"""AWS Service Response Generators.

Response generators for IAM, S3, STS, Secrets Manager, EC2, and IMDS.
"""

import hashlib
import json
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from .generators import generate_access_key_id, random_string


class AWSServiceResponses:
    """Mixin class providing AWS service response generation methods."""

    def __init__(self, account_id: str, region: str):
        self.account_id = account_id
        self.region = region

    # =========================================================================
    # IAM Responses
    # =========================================================================

    def iam_get_user(self, username: str, user_data: Dict) -> Tuple[Dict, int]:
        """Generate GetUser response."""
        return {
            "GetUserResponse": {
                "GetUserResult": {"User": user_data},
                "ResponseMetadata": self._response_metadata(),
            }
        }, 200

    def iam_list_users(self, users: list, max_items: int) -> Tuple[Dict, int]:
        """Generate ListUsers response."""
        user_list = users[:max_items]
        return {
            "ListUsersResponse": {
                "ListUsersResult": {
                    "Users": user_list,
                    "IsTruncated": len(users) > max_items,
                },
                "ResponseMetadata": self._response_metadata(),
            }
        }, 200

    def iam_list_roles(self, roles: list, max_items: int) -> Tuple[Dict, int]:
        """Generate ListRoles response."""
        role_list = roles[:max_items]
        return {
            "ListRolesResponse": {
                "ListRolesResult": {
                    "Roles": role_list,
                    "IsTruncated": len(roles) > max_items,
                },
                "ResponseMetadata": self._response_metadata(),
            }
        }, 200

    def iam_create_access_key(self, username: str) -> Tuple[Dict, int]:
        """Generate CreateAccessKey response - BAIT."""
        return {
            "CreateAccessKeyResponse": {
                "CreateAccessKeyResult": {
                    "AccessKey": {
                        "UserName": username,
                        "AccessKeyId": generate_access_key_id(),
                        "Status": "Active",
                        "SecretAccessKey": f"wJalrXUtnFEMI/K7MDENG/bPxRfiCY{random_string(10)}",
                        "CreateDate": datetime.now(timezone.utc).isoformat() + "Z",
                    }
                },
                "ResponseMetadata": self._response_metadata(),
            }
        }, 200

    # =========================================================================
    # S3 Responses
    # =========================================================================

    def s3_list_buckets(self, buckets: Dict) -> Tuple[Dict, int]:
        """Generate ListBuckets response."""
        bucket_list = [
            {"Name": name, "CreationDate": data["CreationDate"]}
            for name, data in buckets.items()
        ]
        return {
            "ListAllMyBucketsResult": {
                "Owner": {
                    "ID": hashlib.md5(
                        self.account_id.encode(), usedforsecurity=False
                    ).hexdigest(),
                    "DisplayName": "honeypot-owner",
                },
                "Buckets": {"Bucket": bucket_list},
            }
        }, 200

    def s3_list_objects(self, bucket: str, prefix: str = "") -> Tuple[Dict, int]:
        """Generate ListObjectsV2 response."""
        # Generate fake objects
        objects = []
        for i in range(random.randint(5, 20)):
            key = f"{prefix}{'/' if prefix else ''}{random_string(10)}.{'json' if random.random() > 0.5 else 'txt'}"
            objects.append(
                {
                    "Key": key,
                    "LastModified": (
                        datetime.now(timezone.utc)
                        - timedelta(days=random.randint(1, 30))
                    ).isoformat()
                    + "Z",
                    "ETag": f'"{hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()}"',
                    "Size": random.randint(1000, 1000000),
                    "StorageClass": "STANDARD",
                }
            )

        return {
            "ListBucketResult": {
                "Name": bucket,
                "Prefix": prefix,
                "KeyCount": len(objects),
                "MaxKeys": 1000,
                "IsTruncated": False,
                "Contents": objects,
            }
        }, 200

    def s3_get_object(self, bucket: str, key: str) -> Tuple[Dict, int]:
        """Generate GetObject response - BAIT."""
        # Generate fake content based on key extension
        if key.endswith(".json"):
            content = json.dumps(
                {
                    "config": {
                        "database_url": "postgresql://db.internal:5432/prod",
                        "api_key": f"sk-{random_string(32)}",
                        "environment": "production",
                    }
                }
            )
        elif key.endswith(".env"):
            content = f"""# Configuration
DATABASE_URL=postgresql://admin:P@ssw0rd123@db.internal:5432/prod
API_KEY=sk-{random_string(32)}
SECRET_KEY={random_string(64)}
"""
        else:
            content = f"Sample file content for {key}\n" * 10

        return {
            "Body": content,
            "ContentLength": len(content),
            "ContentType": "application/octet-stream",
            "ETag": f'"{hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()}"',
            "LastModified": datetime.now(timezone.utc).isoformat() + "Z",
            "Metadata": {},
        }, 200

    # =========================================================================
    # STS Responses
    # =========================================================================

    def sts_get_caller_identity(self) -> Tuple[Dict, int]:
        """Generate GetCallerIdentity response."""
        return {
            "GetCallerIdentityResponse": {
                "GetCallerIdentityResult": {
                    "Account": self.account_id,
                    "Arn": f"arn:aws:iam::{self.account_id}:user/honeypot-user",
                    "UserId": f"AIDA{random_string(17, string.ascii_uppercase)}",
                },
                "ResponseMetadata": self._response_metadata(),
            }
        }, 200

    def sts_assume_role(self, role_arn: str, session_name: str) -> Tuple[Dict, int]:
        """Generate AssumeRole response - BAIT."""
        return {
            "AssumeRoleResponse": {
                "AssumeRoleResult": {
                    "Credentials": {
                        "AccessKeyId": generate_access_key_id(temp=True),
                        "SecretAccessKey": f"wJalrXUtnFEMI/K7MDENG+bPxRfiCY{random_string(10)}",
                        "SessionToken": f"FwoGZXIvYXdzE{random_string(200)}",
                        "Expiration": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat()
                        + "Z",
                    },
                    "AssumedRoleUser": {
                        "AssumedRoleId": f"AROA{random_string(17)}:{session_name}",
                        "Arn": f"{role_arn}/assumed-role/{session_name}",
                    },
                },
                "ResponseMetadata": self._response_metadata(),
            }
        }, 200

    # =========================================================================
    # Secrets Manager Responses
    # =========================================================================

    def secrets_list_secrets(self, secrets: Dict) -> Tuple[Dict, int]:
        """Generate ListSecrets response."""
        secret_list = [
            {
                "ARN": data["ARN"],
                "Name": data["Name"],
                "Description": data.get("Description", ""),
                "LastChangedDate": data["LastChangedDate"],
                "LastAccessedDate": data["LastAccessedDate"],
            }
            for data in secrets.values()
        ]
        return {
            "SecretList": secret_list,
            "NextToken": None,
        }, 200

    def secrets_get_secret_value(self, secret_data: Dict) -> Tuple[Dict, int]:
        """Generate GetSecretValue response - BAIT."""
        # Generate fake secret value
        secret_value = json.dumps(
            {
                "username": "db_admin",
                "password": f"Pr0d_{random_string(16)}!",
                "host": "db.internal.company.com",
                "port": 5432,
                "database": "production",
            }
        )

        return {
            "ARN": secret_data["ARN"],
            "Name": secret_data["Name"],
            "VersionId": list(secret_data["VersionIdsToStages"].keys())[0],
            "SecretString": secret_value,
            "VersionStages": ["AWSCURRENT"],
            "CreatedDate": secret_data["CreatedDate"],
        }, 200

    # =========================================================================
    # EC2 Responses
    # =========================================================================

    def ec2_describe_instances(self, instances: Dict) -> Tuple[Dict, int]:
        """Generate DescribeInstances response."""
        reservations = []
        for instance_id, instance in instances.items():
            reservations.append(
                {
                    "ReservationId": f"r-{random_string(8)}",
                    "OwnerId": self.account_id,
                    "Instances": [instance],
                }
            )

        return {
            "DescribeInstancesResponse": {
                "reservationSet": {"item": reservations},
                "requestId": random_string(36),
            }
        }, 200

    # =========================================================================
    # IMDS Responses
    # =========================================================================

    def imds_security_credentials(
        self, role_name: str = "honeypot-role"
    ) -> Tuple[Dict, int]:
        """Generate IMDS security credentials - BAIT."""
        return {
            "Code": "Success",
            "LastUpdated": datetime.now(timezone.utc).isoformat() + "Z",
            "Type": "AWS-HMAC",
            "AccessKeyId": generate_access_key_id(temp=True),
            "SecretAccessKey": f"wJalrXUtnFEMI/K7MDENG+bPxRfiCY{random_string(10)}",
            "Token": f"IQoJb3JpZ2luX2VjE{random_string(200)}",
            "Expiration": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
            + "Z",
        }, 200

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _response_metadata(self) -> Dict[str, str]:
        """Generate response metadata."""
        return {
            "RequestId": random_string(36),
        }
