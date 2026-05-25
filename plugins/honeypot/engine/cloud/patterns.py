"""Cloud Management Honeypot - Attack Pattern Detection.

Cloud-specific attack patterns for AWS, Azure, and GCP environments.
Includes SSRF, IAM abuse, metadata service exploitation, and exfiltration patterns.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .models import APICallSeverity, CloudAttackCategory


# ============================================================================
# AWS-Specific Attack Patterns
# ============================================================================

AWS_IAM_ENUMERATION_PATTERNS = [
    # User/Role enumeration
    (r"(?i)(GetUser|ListUsers|GetRole|ListRoles)", "iam_user_enum"),
    (r"(?i)(GetGroup|ListGroups|ListGroupsForUser)", "iam_group_enum"),
    (r"(?i)(ListAttachedUserPolicies|ListUserPolicies)", "iam_policy_enum"),
    (r"(?i)(ListAttachedRolePolicies|ListRolePolicies)", "iam_role_policy_enum"),
    (r"(?i)(GetAccountAuthorizationDetails)", "iam_full_enum"),
    (r"(?i)(SimulatePrincipalPolicy|SimulateCustomPolicy)", "iam_privesc_sim"),
]

AWS_PRIVILEGE_ESCALATION_PATTERNS = [
    # Direct privilege escalation
    (r"(?i)(CreateUser|CreateRole)", "iam_create_principal"),
    (r"(?i)(AttachUserPolicy|AttachRolePolicy)", "iam_attach_policy"),
    (r"(?i)(PutUserPolicy|PutRolePolicy)", "iam_put_policy"),
    (r"(?i)(CreateAccessKey)", "iam_create_key"),
    (r"(?i)(UpdateAssumeRolePolicy)", "iam_update_trust"),
    (r"(?i)(CreateLoginProfile|UpdateLoginProfile)", "iam_console_access"),
    (r"(?i)(AddUserToGroup)", "iam_group_add"),
    # Indirect privilege escalation
    (r"(?i)(CreatePolicyVersion)", "iam_policy_version"),
    (r"(?i)(SetDefaultPolicyVersion)", "iam_policy_default"),
    (r"(?i)(PassRole)", "iam_pass_role"),
]

AWS_S3_EXFILTRATION_PATTERNS = [
    (r"(?i)(ListBuckets)", "s3_bucket_list"),
    (r"(?i)(GetBucketAcl|GetBucketPolicy)", "s3_bucket_acl"),
    (r"(?i)(ListObjects|ListObjectsV2)", "s3_object_list"),
    (r"(?i)(GetObject)", "s3_object_get"),
    (r"(?i)(s3:sync|aws s3 sync)", "s3_bulk_sync"),
    (r"(?i)(PutBucketPolicy|PutBucketAcl)", "s3_policy_modify"),
    (r"(?i)(PutBucketPublicAccessBlock)", "s3_public_access"),
]

AWS_SECRETS_EXTRACTION_PATTERNS = [
    (r"(?i)(GetSecretValue|ListSecrets)", "secrets_manager"),
    (r"(?i)(GetParameter|GetParameters|GetParametersByPath)", "ssm_parameters"),
    (r"(?i)(DecryptKey|Decrypt|GenerateDataKey)", "kms_decrypt"),
    (r"(?i)(DescribeSecret|ListSecretVersionIds)", "secrets_enum"),
]

AWS_METADATA_SERVICE_PATTERNS = [
    # IMDSv1 (vulnerable)
    (r"169\.254\.169\.254", "imds_access"),
    (r"/latest/meta-data/", "imds_metadata"),
    (r"/latest/user-data", "imds_userdata"),
    (r"/latest/api/token", "imds_token"),
    (r"iam/security-credentials", "imds_creds"),
    # EC2 role credential extraction
    (r"/latest/meta-data/iam/security-credentials/", "imds_role_creds"),
]

AWS_LATERAL_MOVEMENT_PATTERNS = [
    (r"(?i)(AssumeRole|AssumeRoleWithSAML|AssumeRoleWithWebIdentity)", "sts_assume"),
    (r"(?i)(GetFederationToken|GetSessionToken)", "sts_token"),
    (r"(?i)(SendCommand|StartSession)", "ssm_command"),
    (r"(?i)(InvokeFunction|Invoke)", "lambda_invoke"),
    (r"(?i)(StartInstances|RunInstances)", "ec2_instance"),
    (r"(?i)(CreateFunction|UpdateFunctionCode)", "lambda_backdoor"),
]

AWS_PERSISTENCE_PATTERNS = [
    (r"(?i)(CreateAccessKey)", "access_key_persist"),
    (r"(?i)(CreateUser.*Backdoor|CreateRole.*Backdoor)", "backdoor_create"),
    (r"(?i)(CreateEventSourceMapping)", "lambda_trigger"),
    (r"(?i)(PutBucketNotification)", "s3_notification"),
    (r"(?i)(CreateTrail|StopLogging|DeleteTrail)", "cloudtrail_tamper"),
]

# ============================================================================
# Generic Cloud Attack Patterns
# ============================================================================

SSRF_PATTERNS = [
    # Internal IPs
    (r"(?:^|[^\d])(127\.0\.0\.1|localhost)", "ssrf_localhost"),
    (r"(?:^|[^\d])(10\.\d{1,3}\.\d{1,3}\.\d{1,3})", "ssrf_class_a"),
    (r"(?:^|[^\d])(172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})", "ssrf_class_b"),
    (r"(?:^|[^\d])(192\.168\.\d{1,3}\.\d{1,3})", "ssrf_class_c"),
    # Cloud metadata services
    (r"169\.254\.169\.254", "ssrf_aws_metadata"),
    (r"metadata\.google\.internal", "ssrf_gcp_metadata"),
    (r"169\.254\.169\.253", "ssrf_azure_metadata"),
    # URL encoding bypass
    (r"(?i)(%2f%2f|%252f%252f)", "ssrf_url_encode"),
    (r"(?i)(0x7f\.0\.0\.1|0177\.0\.0\.1)", "ssrf_octal_hex"),
]

CREDENTIAL_PATTERNS = [
    # AWS credentials
    (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
    (r"ASIA[0-9A-Z]{16}", "aws_temp_key"),
    (r"(?i)(aws_secret_access_key|secret_access_key)\s*[=:]\s*\S+", "aws_secret"),
    # Generic API keys
    (r"(?i)(api[_-]?key|apikey)\s*[=:]\s*\S+", "generic_api_key"),
    (r"(?i)(bearer|authorization)\s*[=:]\s*\S+", "bearer_token"),
    # Other cloud providers
    (r"(?i)(azure[_-]?client[_-]?secret)", "azure_secret"),
    (r"(?i)(gcp[_-]?service[_-]?account)", "gcp_sa"),
]

RECONNAISSANCE_PATTERNS = [
    (r"(?i)(describe|list|get)[A-Z][a-z]+", "api_enumeration"),
    (r"(?i)(version|info|status|health|ping)", "service_probe"),
    (r"(?i)(\.well-known|openid-configuration)", "oidc_probe"),
    (r"(?i)(swagger|openapi|api-docs)", "api_docs_probe"),
]

# ============================================================================
# Pattern Category Mapping
# ============================================================================

PATTERN_CATEGORY_MAP: Dict[str, CloudAttackCategory] = {
    # IAM patterns
    "iam_user_enum": CloudAttackCategory.IAM_ENUMERATION,
    "iam_group_enum": CloudAttackCategory.IAM_ENUMERATION,
    "iam_policy_enum": CloudAttackCategory.IAM_ENUMERATION,
    "iam_role_policy_enum": CloudAttackCategory.IAM_ENUMERATION,
    "iam_full_enum": CloudAttackCategory.IAM_ENUMERATION,
    "iam_privesc_sim": CloudAttackCategory.PRIVILEGE_ESCALATION,
    "iam_create_principal": CloudAttackCategory.BACKDOOR_USER,
    "iam_attach_policy": CloudAttackCategory.PRIVILEGE_ESCALATION,
    "iam_put_policy": CloudAttackCategory.POLICY_MANIPULATION,
    "iam_create_key": CloudAttackCategory.ACCESS_KEY_CREATION,
    "iam_update_trust": CloudAttackCategory.PRIVILEGE_ESCALATION,
    "iam_console_access": CloudAttackCategory.BACKDOOR_USER,
    "iam_group_add": CloudAttackCategory.PRIVILEGE_ESCALATION,
    "iam_policy_version": CloudAttackCategory.POLICY_MANIPULATION,
    "iam_policy_default": CloudAttackCategory.POLICY_MANIPULATION,
    "iam_pass_role": CloudAttackCategory.ROLE_ASSUMPTION,
    # S3 patterns
    "s3_bucket_list": CloudAttackCategory.BUCKET_ENUMERATION,
    "s3_bucket_acl": CloudAttackCategory.BUCKET_ENUMERATION,
    "s3_object_list": CloudAttackCategory.BUCKET_ENUMERATION,
    "s3_object_get": CloudAttackCategory.S3_EXFILTRATION,
    "s3_bulk_sync": CloudAttackCategory.S3_EXFILTRATION,
    "s3_policy_modify": CloudAttackCategory.POLICY_MANIPULATION,
    "s3_public_access": CloudAttackCategory.POLICY_MANIPULATION,
    # Secrets patterns
    "secrets_manager": CloudAttackCategory.SECRETS_EXTRACTION,
    "ssm_parameters": CloudAttackCategory.SECRETS_EXTRACTION,
    "kms_decrypt": CloudAttackCategory.SECRETS_EXTRACTION,
    "secrets_enum": CloudAttackCategory.SECRETS_EXTRACTION,
    # Metadata/SSRF patterns
    "imds_access": CloudAttackCategory.METADATA_SERVICE_ABUSE,
    "imds_metadata": CloudAttackCategory.METADATA_SERVICE_ABUSE,
    "imds_userdata": CloudAttackCategory.METADATA_SERVICE_ABUSE,
    "imds_token": CloudAttackCategory.METADATA_SERVICE_ABUSE,
    "imds_creds": CloudAttackCategory.METADATA_SERVICE_ABUSE,
    "imds_role_creds": CloudAttackCategory.METADATA_SERVICE_ABUSE,
    "ssrf_localhost": CloudAttackCategory.SSRF,
    "ssrf_class_a": CloudAttackCategory.SSRF,
    "ssrf_class_b": CloudAttackCategory.SSRF,
    "ssrf_class_c": CloudAttackCategory.SSRF,
    "ssrf_aws_metadata": CloudAttackCategory.SSRF,
    "ssrf_gcp_metadata": CloudAttackCategory.SSRF,
    "ssrf_azure_metadata": CloudAttackCategory.SSRF,
    "ssrf_url_encode": CloudAttackCategory.SSRF,
    "ssrf_octal_hex": CloudAttackCategory.SSRF,
    # Lateral movement patterns
    "sts_assume": CloudAttackCategory.ROLE_ASSUMPTION,
    "sts_token": CloudAttackCategory.TOKEN_THEFT,
    "ssm_command": CloudAttackCategory.PRIVILEGE_ESCALATION,
    "lambda_invoke": CloudAttackCategory.PRIVILEGE_ESCALATION,
    "ec2_instance": CloudAttackCategory.PRIVILEGE_ESCALATION,
    "lambda_backdoor": CloudAttackCategory.LAMBDA_BACKDOOR,
    # Persistence patterns
    "access_key_persist": CloudAttackCategory.ACCESS_KEY_CREATION,
    "backdoor_create": CloudAttackCategory.BACKDOOR_USER,
    "lambda_trigger": CloudAttackCategory.LAMBDA_BACKDOOR,
    "s3_notification": CloudAttackCategory.LAMBDA_BACKDOOR,
    "cloudtrail_tamper": CloudAttackCategory.LOG_TAMPERING,
    # Credential patterns
    "aws_access_key": CloudAttackCategory.CREDENTIAL_STUFFING,
    "aws_temp_key": CloudAttackCategory.TOKEN_THEFT,
    "aws_secret": CloudAttackCategory.CREDENTIAL_STUFFING,
    "generic_api_key": CloudAttackCategory.CREDENTIAL_STUFFING,
    "bearer_token": CloudAttackCategory.TOKEN_THEFT,
    "azure_secret": CloudAttackCategory.CREDENTIAL_STUFFING,
    "gcp_sa": CloudAttackCategory.CREDENTIAL_STUFFING,
    # Recon patterns
    "api_enumeration": CloudAttackCategory.SERVICE_DISCOVERY,
    "service_probe": CloudAttackCategory.SERVICE_DISCOVERY,
    "oidc_probe": CloudAttackCategory.SERVICE_DISCOVERY,
    "api_docs_probe": CloudAttackCategory.SERVICE_DISCOVERY,
}

# Pattern severity mapping
PATTERN_SEVERITY_MAP: Dict[str, APICallSeverity] = {
    # Critical
    "imds_role_creds": APICallSeverity.CRITICAL,
    "iam_create_key": APICallSeverity.CRITICAL,
    "iam_create_principal": APICallSeverity.CRITICAL,
    "s3_bulk_sync": APICallSeverity.CRITICAL,
    "secrets_manager": APICallSeverity.CRITICAL,
    "kms_decrypt": APICallSeverity.CRITICAL,
    "ssrf_aws_metadata": APICallSeverity.CRITICAL,
    "cloudtrail_tamper": APICallSeverity.CRITICAL,
    "lambda_backdoor": APICallSeverity.CRITICAL,
    # High
    "iam_full_enum": APICallSeverity.HIGH,
    "iam_privesc_sim": APICallSeverity.HIGH,
    "iam_attach_policy": APICallSeverity.HIGH,
    "iam_put_policy": APICallSeverity.HIGH,
    "s3_object_get": APICallSeverity.HIGH,
    "ssm_parameters": APICallSeverity.HIGH,
    "sts_assume": APICallSeverity.HIGH,
    "ssm_command": APICallSeverity.HIGH,
    "ssrf_localhost": APICallSeverity.HIGH,
    "ssrf_class_a": APICallSeverity.HIGH,
    "aws_access_key": APICallSeverity.HIGH,
    # Medium
    "iam_user_enum": APICallSeverity.MEDIUM,
    "iam_group_enum": APICallSeverity.MEDIUM,
    "iam_policy_enum": APICallSeverity.MEDIUM,
    "s3_bucket_list": APICallSeverity.MEDIUM,
    "s3_bucket_acl": APICallSeverity.MEDIUM,
    "s3_object_list": APICallSeverity.MEDIUM,
    "imds_metadata": APICallSeverity.MEDIUM,
    # Low
    "api_enumeration": APICallSeverity.LOW,
    "service_probe": APICallSeverity.LOW,
    "oidc_probe": APICallSeverity.LOW,
    "api_docs_probe": APICallSeverity.LOW,
}


class CloudPatternDetector:
    """Detects cloud-specific attack patterns."""

    def __init__(self):
        """Initialize pattern detector with compiled regexes."""
        self._compiled_patterns: Dict[str, List[Tuple[re.Pattern, str]]] = {}
        self._compile_all_patterns()

    def _compile_all_patterns(self) -> None:
        """Compile all pattern regexes for performance."""
        pattern_groups = {
            "aws_iam_enum": AWS_IAM_ENUMERATION_PATTERNS,
            "aws_privesc": AWS_PRIVILEGE_ESCALATION_PATTERNS,
            "aws_s3_exfil": AWS_S3_EXFILTRATION_PATTERNS,
            "aws_secrets": AWS_SECRETS_EXTRACTION_PATTERNS,
            "aws_metadata": AWS_METADATA_SERVICE_PATTERNS,
            "aws_lateral": AWS_LATERAL_MOVEMENT_PATTERNS,
            "aws_persist": AWS_PERSISTENCE_PATTERNS,
            "ssrf": SSRF_PATTERNS,
            "credentials": CREDENTIAL_PATTERNS,
            "recon": RECONNAISSANCE_PATTERNS,
        }

        for group_name, patterns in pattern_groups.items():
            self._compiled_patterns[group_name] = [
                (re.compile(pattern), name) for pattern, name in patterns
            ]

    def detect(
        self,
        payload: str,
        action: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Detect attack patterns in payload, action, and headers.

        Args:
            payload: Request body or command
            action: API action name (e.g., "GetUser")
            headers: HTTP headers

        Returns:
            List of detected patterns with metadata
        """
        detections = []

        # Combine all text for analysis
        combined = payload or ""
        if action:
            combined += f" {action}"
        if headers:
            combined += " " + " ".join(f"{k}:{v}" for k, v in headers.items())

        # Check all pattern groups
        for group_name, patterns in self._compiled_patterns.items():
            for pattern, name in patterns:
                matches = pattern.findall(combined)
                if matches:
                    category = PATTERN_CATEGORY_MAP.get(
                        name, CloudAttackCategory.UNKNOWN
                    )
                    severity = PATTERN_SEVERITY_MAP.get(name, APICallSeverity.INFO)

                    detections.append(
                        {
                            "pattern_name": name,
                            "pattern_group": group_name,
                            "category": category,
                            "severity": severity,
                            "match_count": len(matches),
                            "sample_matches": matches[:3],  # Limit stored matches
                            "regex": pattern.pattern,
                        }
                    )

        return detections

    def detect_api_action(
        self,
        service: str,
        action: str,
    ) -> Tuple[Optional[CloudAttackCategory], APICallSeverity, List[str]]:
        """Classify an API action by service and action name.

        Args:
            service: Cloud service (iam, s3, ec2, etc.)
            action: API action name (GetUser, ListBuckets, etc.)

        Returns:
            Tuple of (category, severity, pattern_names)
        """
        full_action = f"{service}:{action}"
        detected_patterns = []
        max_severity = APICallSeverity.INFO
        primary_category = None

        # Check against action-specific patterns
        for group_patterns in self._compiled_patterns.values():
            for pattern, name in group_patterns:
                if pattern.search(action) or pattern.search(full_action):
                    detected_patterns.append(name)
                    category = PATTERN_CATEGORY_MAP.get(name)
                    severity = PATTERN_SEVERITY_MAP.get(name, APICallSeverity.INFO)

                    if category and (
                        primary_category is None
                        or self._is_higher_severity(severity, max_severity)
                    ):
                        primary_category = category
                        max_severity = severity

        return primary_category, max_severity, detected_patterns

    def _is_higher_severity(
        self, new: APICallSeverity, current: APICallSeverity
    ) -> bool:
        """Compare severity levels."""
        order = [
            APICallSeverity.INFO,
            APICallSeverity.LOW,
            APICallSeverity.MEDIUM,
            APICallSeverity.HIGH,
            APICallSeverity.CRITICAL,
        ]
        return order.index(new) > order.index(current)

    def get_mitre_techniques(
        self, detected_patterns: List[str]
    ) -> List[Tuple[str, str, str]]:
        """Map detected patterns to MITRE ATT&CK techniques.

        Args:
            detected_patterns: List of pattern names

        Returns:
            List of (technique_id, technique_name, tactic) tuples
        """
        mitre_mapping = {
            # Discovery
            "iam_user_enum": ("T1087.004", "Cloud Account Discovery", "Discovery"),
            "iam_group_enum": ("T1069.003", "Cloud Groups Discovery", "Discovery"),
            "s3_bucket_list": ("T1619", "Cloud Storage Object Discovery", "Discovery"),
            "api_enumeration": ("T1580", "Cloud Infrastructure Discovery", "Discovery"),
            # Credential Access
            "imds_role_creds": (
                "T1552.005",
                "Cloud Instance Metadata API",
                "Credential Access",
            ),
            "secrets_manager": (
                "T1555",
                "Credentials from Password Stores",
                "Credential Access",
            ),
            "aws_access_key": (
                "T1552.001",
                "Credentials In Files",
                "Credential Access",
            ),
            # Privilege Escalation
            "iam_attach_policy": (
                "T1098.003",
                "Additional Cloud Roles",
                "Privilege Escalation",
            ),
            "iam_create_principal": (
                "T1136.003",
                "Cloud Account",
                "Privilege Escalation",
            ),
            "sts_assume": (
                "T1548.005",
                "Temporary Elevated Cloud Access",
                "Privilege Escalation",
            ),
            # Lateral Movement
            "ssm_command": ("T1021.007", "Cloud Services", "Lateral Movement"),
            "lambda_invoke": ("T1648", "Serverless Execution", "Lateral Movement"),
            # Collection/Exfiltration
            "s3_object_get": ("T1530", "Data from Cloud Storage", "Collection"),
            "s3_bulk_sync": (
                "T1567.002",
                "Exfiltration to Cloud Storage",
                "Exfiltration",
            ),
            # Persistence
            "lambda_backdoor": ("T1098.003", "Additional Cloud Roles", "Persistence"),
            "access_key_persist": (
                "T1098.001",
                "Additional Cloud Credentials",
                "Persistence",
            ),
            # Defense Evasion
            "cloudtrail_tamper": ("T1562.008", "Disable Cloud Logs", "Defense Evasion"),
        }

        techniques = []
        seen_ids = set()

        for pattern in detected_patterns:
            if pattern in mitre_mapping:
                technique_id, technique_name, tactic = mitre_mapping[pattern]
                if technique_id not in seen_ids:
                    techniques.append((technique_id, technique_name, tactic))
                    seen_ids.add(technique_id)

        return techniques


# Singleton instance
_detector_instance: Optional[CloudPatternDetector] = None


def get_cloud_pattern_detector() -> CloudPatternDetector:
    """Get singleton pattern detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = CloudPatternDetector()
    return _detector_instance
