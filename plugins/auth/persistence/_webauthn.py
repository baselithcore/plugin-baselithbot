"""WebAuthn / passkey credential persistence."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger
from plugins.auth.webauthn import WebAuthnCredential

logger = get_logger(__name__)


def _row_to_credential(row: dict) -> WebAuthnCredential:
    return WebAuthnCredential(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        credential_id=bytes(row["credential_id"]),
        public_key=bytes(row["public_key"]),
        sign_count=row.get("sign_count", 0),
        transports=row.get("transports"),
        aaguid=bytes(row["aaguid"]) if row.get("aaguid") else None,
        name=row.get("name"),
        created_at=row.get("created_at"),
        last_used=row.get("last_used"),
    )


class WebAuthnPersistenceMixin:
    """CRUD for passkey credentials."""

    def add_webauthn_credential(
        self, cred: WebAuthnCredential, name: Optional[str] = None
    ) -> WebAuthnCredential:
        """Persist a newly registered passkey credential."""
        cred_id = str(uuid.uuid4())
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_webauthn_credentials
                        (id, user_id, credential_id, public_key, sign_count,
                         transports, aaguid, name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cred_id,
                        cred.user_id,
                        cred.credential_id,
                        cred.public_key,
                        cred.sign_count,
                        cred.transports,
                        cred.aaguid,
                        name or cred.name,
                    ),
                )
            conn.commit()
        cred.id = cred_id
        cred.name = name or cred.name
        return cred

    def list_webauthn_credentials(self, user_id: str) -> List[WebAuthnCredential]:
        """List a user's passkey credentials."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM auth_webauthn_credentials WHERE user_id = %s "
                "ORDER BY created_at DESC",
                (user_id,),
            )
            return [_row_to_credential(r) for r in cur.fetchall()]

    def get_webauthn_by_credential_id(
        self, credential_id: bytes
    ) -> Optional[WebAuthnCredential]:
        """Look up a credential by its raw credential_id (passkey login)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM auth_webauthn_credentials WHERE credential_id = %s",
                (credential_id,),
            )
            row = cur.fetchone()
            return _row_to_credential(row) if row else None

    def update_webauthn_sign_count(self, db_id: str, sign_count: int) -> None:
        """Persist the updated signature counter after an assertion."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_webauthn_credentials "
                    "SET sign_count = %s, last_used = %s WHERE id = %s",
                    (sign_count, datetime.now(timezone.utc), db_id),
                )
            conn.commit()

    def rename_webauthn_credential(self, user_id: str, db_id: str, name: str) -> bool:
        """Rename a user's own passkey."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_webauthn_credentials SET name = %s "
                    "WHERE id = %s AND user_id = %s",
                    (name, db_id, user_id),
                )
                ok = cur.rowcount > 0
            conn.commit()
        return ok

    def delete_webauthn_credential(self, user_id: str, db_id: str) -> bool:
        """Delete a user's own passkey."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_webauthn_credentials "
                    "WHERE id = %s AND user_id = %s",
                    (db_id, user_id),
                )
                ok = cur.rowcount > 0
            conn.commit()
        return ok
