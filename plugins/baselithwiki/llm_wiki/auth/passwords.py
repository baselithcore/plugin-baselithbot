"""Re-export password helpers per coerenza API.

Le funzioni vivono in :mod:`llm_wiki.db.users` perché sono usate dal
livello DB (create_user persiste l'hash subito), ma l'API pubblica
``llm_wiki.auth.passwords`` chiarisce che sono primitive di sicurezza.

Pattern allineato a ``agent-jira`` (anche lì duplicato fra
``app/db/users.py`` e ``app/security.py``).
"""

from __future__ import annotations

from llm_wiki.db.users import hash_password, verify_password

__all__ = ["hash_password", "verify_password"]
