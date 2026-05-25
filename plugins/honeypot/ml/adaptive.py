"""Adaptive Response Generator for Dynamic Bait Creation.

Generates tailored bait content based on predicted attacker TTPs
to maximize dwell time and intelligence collection.

Bait types include:
- Fake credentials (SSH keys, AWS credentials, database passwords)
- Canary tokens with external webhook triggers
- Attractive file targets (wallets, configs, backups)
"""

import hashlib
from core.observability.logging import get_logger
import secrets
import string
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..emulation.models import BaitContent, SessionState, TTP, TTPPrediction

logger = get_logger(__name__)


# Template generators for different bait types
BAIT_TEMPLATES = {
    "ssh_key": {
        "path": "~/.ssh/{name}",
        "content_type": "ssh_private_key",
        "priority": "high",
    },
    "aws_credentials": {
        "path": "~/.aws/credentials",
        "content_type": "aws_creds",
        "priority": "critical",
    },
    "kube_config": {
        "path": "~/.kube/config",
        "content_type": "kube_config",
        "priority": "high",
    },
    "database_config": {
        "path": "/etc/{app}/database.yml",
        "content_type": "db_creds",
        "priority": "high",
    },
    "env_file": {
        "path": "/var/www/{app}/.env",
        "content_type": "env_file",
        "priority": "medium",
    },
    "backup_archive": {
        "path": "/backup/{name}.tar.gz.enc",
        "content_type": "encrypted_backup",
        "priority": "medium",
    },
    "wallet_file": {
        "path": "~/.bitcoin/wallet.dat",
        "content_type": "crypto_wallet",
        "priority": "critical",
    },
}


class AdaptiveResponseGenerator:
    """Generate adaptive bait content based on TTP predictions.

    Uses predicted TTPs to create tailored baits that match
    attacker interests and maximize engagement.

    Example:
        >>> generator = AdaptiveResponseGenerator()
        >>> predictions = [TTPPrediction(ttp=TTP.CREDENTIAL_DUMPING, confidence=0.9)]
        >>> baits = await generator.generate_bait(predictions, session)
        >>> for bait in baits:
        ...     print(f"Injecting bait at {bait.path}")
    """

    def __init__(
        self,
        max_baits_per_session: int = 5,
        enable_canary_tokens: bool = True,
        webhook_url: Optional[str] = None,
    ):
        """Initialize adaptive response generator.

        Args:
            max_baits_per_session: Maximum baits to generate per session
            enable_canary_tokens: Whether to generate canary tokens
            webhook_url: External webhook for canary triggers
        """
        self.max_baits_per_session = max_baits_per_session
        self.enable_canary_tokens = enable_canary_tokens
        self.webhook_url = webhook_url

        # Track generated baits per session
        self._session_baits: Dict[str, List[str]] = {}

    async def generate_bait(
        self,
        predictions: List[TTPPrediction],
        session: SessionState,
    ) -> List[BaitContent]:
        """Generate bait content based on TTP predictions.

        Args:
            predictions: Predicted TTPs with confidence scores
            session: Current session state

        Returns:
            List of BaitContent to inject
        """
        baits = []

        # Get existing baits for this session
        existing = self._session_baits.get(session.session_id, [])
        available_slots = self.max_baits_per_session - len(existing)

        if available_slots <= 0:
            return baits

        # Generate baits for each prediction
        for pred in predictions:
            if len(baits) >= available_slots:
                break

            bait = self._generate_bait_for_ttp(pred.ttp, session)
            if bait and bait.path not in existing:
                baits.append(bait)
                existing.append(bait.path)

        # Update tracking
        self._session_baits[session.session_id] = existing

        return baits

    def _generate_bait_for_ttp(
        self,
        ttp: TTP,
        session: SessionState,
    ) -> Optional[BaitContent]:
        """Generate bait content targeted at specific TTP.

        Args:
            ttp: Target TTP
            session: Session context

        Returns:
            BaitContent or None if no suitable bait
        """
        # Map TTPs to bait types
        ttp_bait_map = {
            TTP.CREDENTIAL_DUMPING: ["ssh_key", "aws_credentials", "database_config"],
            TTP.UNSECURED_CREDENTIALS: [
                "env_file",
                "database_config",
                "aws_credentials",
            ],
            TTP.SSH_AUTHORIZED_KEYS: ["ssh_key"],
            TTP.FILE_DISCOVERY: ["backup_archive", "wallet_file", "env_file"],
            TTP.DATA_FROM_LOCAL: ["backup_archive", "wallet_file", "database_config"],
            TTP.RESOURCE_HIJACKING: ["wallet_file", "aws_credentials", "kube_config"],
        }

        bait_types = ttp_bait_map.get(ttp, ["env_file"])

        # Try to generate first available bait type
        for bait_type in bait_types:
            template = BAIT_TEMPLATES.get(bait_type)
            if template:
                return self._create_bait_from_template(
                    bait_type,
                    template,
                    session,
                )

        return None

    def _create_bait_from_template(
        self,
        bait_type: str,
        template: Dict,
        session: SessionState,
    ) -> BaitContent:
        """Create bait content from template.

        Args:
            bait_type: Type of bait
            template: Template configuration
            session: Session context

        Returns:
            Generated BaitContent
        """
        # Generate path with substitutions
        path = template["path"]
        path = path.replace("~", session.home_dir)
        path = path.replace("{name}", self._generate_realistic_name(bait_type))
        path = path.replace("{app}", self._generate_app_name())

        # Generate content
        content = self._generate_content(template["content_type"], session)

        # Generate canary token if enabled
        canary_token = None
        if self.enable_canary_tokens:
            canary_token = self._generate_canary_token(session, path)

        return BaitContent(
            path=path,
            content=content,
            trigger_on_access=True,
            alert_priority=template["priority"],
            external_webhook=bool(self.webhook_url),
            canary_token=canary_token,
            ttl_minutes=60,
        )

    def _generate_content(self, content_type: str, session: SessionState) -> str:
        """Generate realistic bait content.

        Args:
            content_type: Type of content to generate
            session: Session context

        Returns:
            Generated content string
        """
        if content_type == "ssh_private_key":
            return self._generate_fake_ssh_key()
        elif content_type == "aws_creds":
            return self._generate_fake_aws_credentials()
        elif content_type == "kube_config":
            return self._generate_fake_kube_config()
        elif content_type == "db_creds":
            return self._generate_fake_db_config()
        elif content_type == "env_file":
            return self._generate_fake_env_file()
        elif content_type == "encrypted_backup":
            return self._generate_fake_backup_info()
        elif content_type == "crypto_wallet":
            return self._generate_fake_wallet()
        else:
            return f"# Configuration file\n# Generated: {datetime.now(timezone.utc).isoformat()}"

    def _generate_fake_ssh_key(self) -> str:
        """Generate fake SSH private key."""
        # This looks like a real key but is not cryptographically valid
        key_data = "".join(
            secrets.choice(string.ascii_letters + string.digits + "+/")
            for _ in range(1600)
        )

        # Format with line breaks
        lines = [key_data[i : i + 64] for i in range(0, len(key_data), 64)]

        return (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            + "\n".join(lines)
            + "\n-----END OPENSSH PRIVATE KEY-----\n"
        )

    def _generate_fake_aws_credentials(self) -> str:
        """Generate fake AWS credentials file."""
        access_key = "AKIA" + "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16)
        )
        secret_key = "".join(
            secrets.choice(string.ascii_letters + string.digits + "+/")
            for _ in range(40)
        )

        return f"""[default]
aws_access_key_id = {access_key}
aws_secret_access_key = {secret_key}
region = us-east-1

[production]
aws_access_key_id = AKIA{secrets.token_hex(8).upper()}
aws_secret_access_key = {secrets.token_urlsafe(30)}
region = eu-west-1

# DO NOT COMMIT - production credentials
# Last rotated: 2025-12-15
"""

    def _generate_fake_kube_config(self) -> str:
        """Generate fake Kubernetes config."""
        token = secrets.token_urlsafe(64)

        return f"""apiVersion: v1
kind: Config
preferences: {{}}
clusters:
- cluster:
    server: https://k8s.internal.company.com:6443
    certificate-authority-data: LS0tLS1CRUdJTi...
  name: production-cluster
contexts:
- context:
    cluster: production-cluster
    user: admin
  name: production
current-context: production
users:
- name: admin
  user:
    token: {token}
"""

    def _generate_fake_db_config(self) -> str:
        """Generate fake database configuration."""
        password = secrets.token_urlsafe(16)

        return f"""production:
  adapter: postgresql
  database: company_production
  host: db-master.internal.company.com
  port: 5432
  username: app_user
  password: {password}
  pool: 25
  
staging:
  adapter: postgresql
  database: company_staging
  host: db-staging.internal.company.com
  port: 5432
  username: staging_user
  password: stg_{secrets.token_hex(8)}
  pool: 5

# WARNING: Contains production credentials
# Contact: devops@company.com
"""

    def _generate_fake_env_file(self) -> str:
        """Generate fake .env file."""
        return f"""# Application Environment Variables
# DO NOT COMMIT TO VERSION CONTROL

NODE_ENV=production
PORT=3000

# Database
DATABASE_URL=postgresql://admin:{secrets.token_urlsafe(12)}@db.internal:5432/app_prod

# Redis
REDIS_URL=redis://:{secrets.token_hex(16)}@redis.internal:6379/0

# API Keys
STRIPE_SECRET_KEY=sk_live_{secrets.token_hex(24)}
SENDGRID_API_KEY=SG.{secrets.token_urlsafe(22)}.{secrets.token_urlsafe(43)}
AWS_ACCESS_KEY_ID=AKIA{secrets.token_hex(8).upper()}
AWS_SECRET_ACCESS_KEY={secrets.token_urlsafe(30)}

# JWT
JWT_SECRET={secrets.token_hex(32)}

# Last Updated: 2025-11-20
"""

    def _generate_fake_backup_info(self) -> str:
        """Generate fake encrypted backup metadata."""
        return f"""# Encrypted Backup Archive
# Created: {datetime.now(timezone.utc).isoformat()}
# Encryption: AES-256-GCM
# 
# To decrypt:
#   openssl enc -d -aes-256-cbc -in backup.tar.gz.enc -out backup.tar.gz \\
#     -pass pass:{secrets.token_urlsafe(24)}
#
# Contains: database dump, config files, SSL certificates
# Size: 2.4GB (encrypted)
# Checksum: sha256:{secrets.token_hex(32)}
"""

    def _generate_fake_wallet(self) -> str:
        """Generate fake cryptocurrency wallet data."""
        # Generate fake Bitcoin-like addresses
        address = "1" + "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(33)
        )

        return f"""# Bitcoin Core Wallet
# Created: 2024-03-15
# 
# WARNING: Contains private keys
# Backup passphrase: {secrets.token_urlsafe(20)}
#
# Primary address: {address}
# Balance: 2.45831 BTC
#
# ENCRYPTED - DO NOT SHARE
{secrets.token_hex(256)}
"""

    def _generate_realistic_name(self, bait_type: str) -> str:
        """Generate realistic file name for bait type."""
        names = {
            "ssh_key": ["id_rsa", "id_ed25519", "deploy_key", "github_rsa"],
            "backup_archive": ["db_backup_2025", "full_backup", "config_backup"],
        }

        import random

        options = names.get(bait_type, ["file"])
        return random.choice(options)

    def _generate_app_name(self) -> str:
        """Generate realistic application name."""
        import random

        apps = ["webapp", "api", "backend", "app", "service", "mysql", "postgresql"]
        return random.choice(apps)

    def _generate_canary_token(self, session: SessionState, path: str) -> str:
        """Generate unique canary token for tracking.

        Args:
            session: Session context
            path: Bait file path

        Returns:
            Unique token string
        """
        data = f"{session.session_id}:{path}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_bait_stats(self) -> Dict[str, int]:
        """Get statistics on generated baits.

        Returns:
            Dict with bait counts per session
        """
        return {
            "total_sessions": len(self._session_baits),
            "total_baits": sum(len(b) for b in self._session_baits.values()),
        }

    def clear_session(self, session_id: str) -> None:
        """Clear bait tracking for a session.

        Args:
            session_id: Session to clear
        """
        self._session_baits.pop(session_id, None)
