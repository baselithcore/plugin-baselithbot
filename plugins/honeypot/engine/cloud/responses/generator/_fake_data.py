"""Fake data factory mixin for CloudResponseGenerator."""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from ..generators import (
    random_string,
)


class FakeDataMixin:
    """Mixin providing _create_* factory methods for fake AWS data."""

    def _create_user(self, name: str) -> Dict[str, Any]:
        """Create a fake IAM user."""
        create_date = datetime.now(timezone.utc) - timedelta(
            days=random.randint(30, 365)
        )
        return {
            "UserName": name,
            "UserId": f"AIDA{random_string(17)}",
            "Arn": f"arn:aws:iam::{self.account_id}:user/{name}",
            "CreateDate": create_date.isoformat() + "Z",
            "PasswordLastUsed": (
                create_date + timedelta(days=random.randint(1, 30))
            ).isoformat()
            + "Z",
            "Tags": [
                {
                    "Key": "Environment",
                    "Value": random.choice(["prod", "staging", "dev"]),
                },
                {
                    "Key": "Team",
                    "Value": random.choice(["platform", "security", "devops"]),
                },
            ],
        }

    def _create_role(self, name: str) -> Dict[str, Any]:
        """Create a fake IAM role."""
        create_date = datetime.now(timezone.utc) - timedelta(
            days=random.randint(30, 365)
        )
        return {
            "RoleName": name,
            "RoleId": f"AROA{random_string(17)}",
            "Arn": f"arn:aws:iam::{self.account_id}:role/{name}",
            "CreateDate": create_date.isoformat() + "Z",
            "AssumeRolePolicyDocument": json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
            "MaxSessionDuration": 3600,
        }

    def _create_bucket(self, name: str) -> Dict[str, Any]:
        """Create a fake S3 bucket."""
        create_date = datetime.now(timezone.utc) - timedelta(
            days=random.randint(30, 365)
        )
        return {
            "Name": name,
            "CreationDate": create_date.isoformat() + "Z",
            "LocationConstraint": self.region if self.region != "us-east-1" else None,
        }

    def _create_secret(self, name: str) -> Dict[str, Any]:
        """Create a fake Secrets Manager secret."""
        create_date = datetime.now(timezone.utc) - timedelta(
            days=random.randint(30, 365)
        )
        return {
            "ARN": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:{name}-{random_string(6)}",
            "Name": name,
            "Description": f"Credentials for {name.split('/')[-1]}",
            "LastChangedDate": (
                create_date + timedelta(days=random.randint(1, 30))
            ).timestamp(),
            "LastAccessedDate": datetime.now(timezone.utc).timestamp(),
            "VersionIdsToStages": {
                f"v{random_string(32)}": ["AWSCURRENT"],
            },
            "CreatedDate": create_date.timestamp(),
        }

    def _create_instance(self, instance_id: str) -> Dict[str, Any]:
        """Create a fake EC2 instance."""
        launch_time = datetime.now(timezone.utc) - timedelta(
            hours=random.randint(1, 720)
        )
        instance_types = ["t3.micro", "t3.medium", "m5.large", "c5.xlarge"]
        return {
            "InstanceId": instance_id,
            "InstanceType": random.choice(instance_types),
            "LaunchTime": launch_time.isoformat() + "Z",
            "State": {"Code": 16, "Name": "running"},
            "PrivateIpAddress": f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "PublicIpAddress": f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "VpcId": f"vpc-{random_string(8)}",
            "SubnetId": f"subnet-{random_string(8)}",
            "Tags": [
                {"Key": "Name", "Value": f"server-{random_string(4)}"},
                {"Key": "Environment", "Value": random.choice(["prod", "staging"])},
            ],
        }
