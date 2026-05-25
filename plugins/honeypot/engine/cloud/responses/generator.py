"""Cloud Response Generator.

Main generator class for AWS-like API responses.
"""

import hashlib
import json
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from .aws_services import AWSServiceResponses
from .generators import (
    generate_account_id,
    generate_bucket_name,
    generate_instance_id,
    generate_secret_name,
    random_string,
)
from .templates import AWS_ERROR_TEMPLATES


class CloudResponseGenerator(AWSServiceResponses):
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

    # =========================================================================
    # Public API Methods
    # =========================================================================

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

        # High-Fidelity AWS Console Login Replica
        html = f"""<!DOCTYPE html>
<html class="a-no-js" data-19ax5a9jf="dingo" lang="en-US">
<head>
<meta charset="utf-8"/>
<title>Amazon Web Services Sign-In</title>
<meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0" name="viewport"/>
<style>
@font-face {{
  font-family: "Amazon Ember";
  src: local("Arial");
  font-weight: 400;
}}
@font-face {{
  font-family: "Amazon Ember";
  src: local("Arial-Bold");
  font-weight: 700;
}}
body, html {{
    height: 100%;
    margin: 0;
    padding: 0;
    background-color: #232f3e;
    font-family: "Amazon Ember", "Helvetica Neue", Roboto, Arial, sans-serif;
    color: #16191f;
    font-size: 14px;
    line-height: 1.4;
}}
.aws-signin-wrapper {{
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: #f2f3f3;
}}
.aws-signin-header {{
    text-align: center;
    padding: 24px 0;
    margin-bottom: 0;
}}
.aws-logo {{
    width: 60px;
    height: 36px;
    margin: 0 auto;
}}
/* Authentic AWS Logo (from simple-icons) */
.aws-logo-svg {{
    fill: #232F3E;
    height: 60px;
    width: 60px; 
}}

.aws-signin-content {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 0 10px;
}}
.aws-signin-form {{
    background-color: #fff;
    width: 100%;
    max-width: 400px;
    border-radius: 4px;
    box-shadow: 0 1px 3px 0 rgba(0,0,0,.1);
    padding: 24px 40px;
    box-sizing: border-box;
    margin-top: 20px;
}}
h1 {{
    font-size: 20px;
    font-weight: 700;
    margin: 0 0 20px;
    color: #16191f;
}}
.form-group {{
    margin-bottom: 16px;
}}
label {{
    display: block;
    font-weight: 700;
    margin-bottom: 6px;
    color: #545b64;
    font-size: 14px;
}}
input[type="text"], input[type="password"] {{
    width: 100%;
    height: 32px;
    padding: 4px 10px;
    border: 1px solid #879596;
    border-radius: 2px;
    box-sizing: border-box;
    font-size: 14px;
    box-shadow: 0 1px 0 rgba(255,255,255,.5), 0 1px 0 rgba(0,0,0,.07) inset;
    outline: none;
    transition: all 0.1s linear;
}}
input[type="text"]:focus, input[type="password"]:focus {{
    border-color: #e77600;
    box-shadow: 0 0 3px 2px rgba(227,118,0,.5), 0 1px 0 rgba(0,0,0,.07) inset;
}}
.btn-primary {{
    background: linear-gradient(to bottom, #f7dfa5, #f0c14b);
    border-color: #a88734 #9c7e31 #846a29;
    color: #111;
    display: block;
    width: 100%;
    text-align: center;
    padding: 0;
    height: 29px;
    border-width: 1px;
    border-style: solid;
    border-radius: 2px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 400;
    box-shadow: 0 1px 0 rgba(255,255,255,.4) inset;
}}
.btn-primary:hover {{
    background: linear-gradient(to bottom, #f5d78e, #eeb933);
}}
.btn-primary:active {{
    background: #f0c14b;
    border-color: #cdb933 #b69d30 #9c8328;
    box-shadow: 0 1px 3px rgba(0,0,0,.2) inset;
}}
.btn-text {{
    line-height: 29px;
}}
.forgot-password {{
    margin-top: 16px;
    font-size: 12px;
    text-align: right;
}}
.forgot-password a {{
    color: #007eb9;
    text-decoration: none;
}}
.forgot-password a:hover {{
    text-decoration: underline;
    color: #e47911;
}}
.aws-signin-footer {{
    text-align: center;
    padding: 30px 0;
    font-size: 11px;
    color: #545b64;
    background-color: #f2f3f3; /* Blend with body */
}}
.aws-signin-footer ul {{
    list-style: none;
    padding: 0;
    margin: 0;
}}
.aws-signin-footer li {{
    display: inline-block;
    margin: 0 8px;
}}
.aws-signin-footer a {{
    color: #007eb9;
    text-decoration: none;
}}
.aws-signin-footer a:hover {{
    text-decoration: underline;
    color: #e47911;
}}
.notice {{
    color: #545b64;
    font-size: 11px;
    margin-top: 20px;
    line-height: 1.4;
}}
.alert-box {{
    border: 1px solid #c5c5c5;
    background-color: #fff;
    padding: 14px;
    margin-bottom: 20px;
    border-radius: 4px;
    display: none;
    font-size: 13px;
}}
.user-type-selector {{
    margin-bottom: 20px;
    display: flex;
    border-bottom: 1px solid #d5dbdb;
}}
.user-type {{
    padding: 8px 0;
    margin-right: 20px;
    font-size: 14px;
    cursor: pointer;
    color: #545b64;
    font-weight: 700;
    position: relative;
}}
.user-type.active {{
    color: #16191f;
    border-bottom: 3px solid #e77600;
    margin-bottom: -2px;
}}
</style>
<script>
    function switchTab(type) {{
        document.getElementById('tab-root').classList.remove('active');
        document.getElementById('tab-iam').classList.remove('active');
        
        if (type === 'root') {{
            document.getElementById('tab-root').classList.add('active');
            document.getElementById('root-fields').style.display = 'block';
            document.getElementById('iam-fields').style.display = 'none';
            document.getElementById('root_email').required = true;
            document.getElementById('account').required = false;
            document.getElementById('username').required = false;
            document.getElementById('password').required = false; // Usually Next button follows, but simplified here
        }} else {{
            document.getElementById('tab-iam').classList.add('active');
            document.getElementById('root-fields').style.display = 'none';
            document.getElementById('iam-fields').style.display = 'block';
            document.getElementById('root_email').required = false;
            document.getElementById('account').required = true;
            document.getElementById('username').required = true;
            document.getElementById('password').required = true;
        }}
    }}
</script>
</head>
<body>
    <div class="aws-signin-wrapper">
        <div class="aws-signin-header">
            <svg class="aws-logo-svg" role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>Amazon Web Services</title><path d="M6.763 10.036c0 .296.032.535.088.71.064.176.144.368.256.576.04.063.056.127.056.183 0 .08-.048.16-.152.24l-.503.335a.383.383 0 0 1-.208.072c-.08 0-.16-.04-.239-.112a2.47 2.47 0 0 1-.287-.375 6.18 6.18 0 0 1-.248-.471c-.622.734-1.405 1.101-2.347 1.101-.67 0-1.205-.191-1.596-.574-.391-.384-.59-.894-.59-1.533 0-.678.239-1.23.726-1.644.487-.415 1.133-.623 1.955-.623.272 0 .551.024.846.064.296.04.6.104.918.176v-.583c0-.607-.127-1.03-.375-1.277-.255-.248-.686-.367-1.3-.367-.28 0-.568.031-.863.103-.295.072-.583.16-.862.272a2.287 2.287 0 0 1-.28.104.488.488 0 0 1-.127.023c-.112 0-.168-.08-.168-.247v-.391c0-.128.016-.224.056-.28a.597.597 0 0 1 .224-.167c.279-.144.614-.264 1.005-.36a4.84 4.84 0 0 1 1.246-.151c.95 0 1.644.216 2.091.647.439.43.662 1.085.662 1.963v2.586zm-3.24 1.214c.263 0 .534-.048.822-.144.287-.096.543-.271.758-.51.128-.152.224-.32.272-.512.047-.191.08-.423.08-.694v-.335a6.66 6.66 0 0 0-.735-.136 6.02 6.02 0 0 0-.75-.048c-.535 0-.926.104-1.19.32-.263.215-.39.518-.39.917 0 .375.095.655.295.846.191.2.47.296.838.296zm6.41.862c-.144 0-.24-.024-.304-.08-.064-.048-.12-.16-.168-.311L7.586 5.55a1.398 1.398 0 0 1-.072-.32c0-.128.064-.2.191-.2h.783c.151 0 .255.025.31.08.065.048.113.16.16.312l1.342 5.284 1.245-5.284c.04-.16.088-.264.151-.312a.549.549 0 0 1 .32-.08h.638c.152 0 .256.025.32.08.063.048.12.16.151.312l1.261 5.348 1.381-5.348c.048-.16.104-.264.16-.312a.52.52 0 0 1 .311-.08h.743c.127 0 .2.065.2.2 0 .04-.009.08-.017.128a1.137 1.137 0 0 1-.056.2l-1.923 6.17c-.048.16-.104.263-.168.311a.51.51 0 0 1-.303.08h-.687c-.151 0-.255-.024-.32-.08-.063-.056-.119-.16-.15-.32l-1.238-5.148-1.23 5.14c-.04.16-.087.264-.15.32-.065.056-.177.08-.32.08zm10.256.215c-.415 0-.83-.048-1.229-.143-.399-.096-.71-.2-.918-.32-.128-.071-.215-.151-.247-.223a.563.563 0 0 1-.048-.224v-.407c0-.167.064-.247.183-.247.048 0 .096.008.144.024.048.016.12.048.2.08.271.12.566.215.878.279.319.064.63.096.95.096.502 0 .894-.088 1.165-.264a.86.86 0 0 0 .415-.758.777.777 0 0 0-.215-.559c-.144-.151-.416-.287-.807-.415l-1.157-.36c-.583-.183-1.014-.454-1.277-.813a1.902 1.902 0 0 1-.4-1.158c0-.335.073-.63.216-.886.144-.255.335-.479.575-.654.24-.184.51-.32.83-.415.32-.096.655-.136 1.006-.136.175 0 .359.008.535.032.183.024.35.056.518.088.16.04.312.08.455.127.144.048.256.096.336.144a.69.69 0 0 1 .24.2.43.43 0 0 1 .071.263v.375c0 .168-.064.256-.184.256a.83.83 0 0 1-.303-.096 3.652 3.652 0 0 0-1.532-.311c-.455 0-.815.071-1.062.223-.248.152-.375.383-.375.71 0 .224.08.416.24.567.159.152.454.304.877.44l1.134.358c.574.184.99.44 1.237.767.247.327.367.702.367 1.117 0 .343-.072.655-.207.926-.144.272-.336.511-.583.703-.248.2-.543.343-.886.447-.36.111-.734.167-1.142.167zM21.698 16.207c-2.626 1.94-6.442 2.969-9.722 2.969-4.598 0-8.74-1.7-11.87-4.526-.247-.223-.024-.527.272-.351 3.384 1.963 7.559 3.153 11.877 3.153 2.914 0 6.114-.607 9.06-1.852.439-.2.814.287.383.607zM22.792 14.961c-.336-.43-2.22-.207-3.074-.103-.255.032-.295-.192-.063-.36 1.5-1.053 3.967-.75 4.254-.399.287.36-.08 2.826-1.485 4.007-.215.184-.423.088-.327-.151.32-.79 1.03-2.57.695-2.994z"/></svg>
        </div>
        <div class="aws-signin-content">
            <div class="aws-signin-form">
                <h1>Sign in</h1>
                
                <div class="user-type-selector">
                    <div id="tab-root" class="user-type" onclick="switchTab('root')">Root user</div>
                    <div id="tab-iam" class="user-type active" onclick="switchTab('iam')">IAM user</div>
                </div>

                <form method="POST" action="/console/login">
                    <input type="hidden" name="csrf_token" value="{token}">
                    
                    <div id="root-fields" style="display:none;">
                        <div class="form-group">
                            <label for="root_email">Root user email address</label>
                            <input type="text" id="root_email" name="root_email">
                        </div>
                    </div>

                    <div id="iam-fields">
                        <div class="form-group">
                            <label for="account">Account ID (12 digits) or account alias</label>
                            <input type="text" id="account" name="account" required placeholder="" autofocus>
                        </div>

                        <div class="form-group">
                            <label for="username">IAM user name</label>
                            <input type="text" id="username" name="username" required>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>

                    <button type="submit" class="btn-primary">
                        <span class="btn-text">Sign in</span>
                    </button>

                    <div class="forgot-password">
                        <a href="https://signin.aws.amazon.com/forgotpassword" target="_blank" rel="noopener noreferrer">Forgot password?</a>
                    </div>
                </form>
            </div>
        </div>
        <div class="aws-signin-footer">
            <ul>
                <li><a href="https://aws.amazon.com/privacy/?nc1=f_pr" target="_blank" rel="noopener noreferrer">Privacy</a></li>
                <li><a href="https://aws.amazon.com/terms/?nc1=f_pr" target="_blank" rel="noopener noreferrer">Terms</a></li>
                <li><a href="https://aws.amazon.com/legal/cookies/" target="_blank" rel="noopener noreferrer">Cookie preferences</a></li>
            </ul>
            <div class="notice">
                &copy; 2023-{datetime.now().year}, Amazon Web Services, Inc. or its affiliates. All rights reserved.
            </div>
        </div>
    </div>
</body>
</html>"""
        return html, 200

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

    # =========================================================================
    # Error Handling
    # =========================================================================

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

    # =========================================================================
    # Action Router
    # =========================================================================

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
