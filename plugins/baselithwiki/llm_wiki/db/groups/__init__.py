"""CRUD gruppi + membership + assegnazione ruoli.

Tabelle: ``groups``, ``group_members``, ``group_roles``. Schema in
``alembic/versions/015_groups.py``.

Modello bundle-utenti AWS IAM-style: un gruppo collega N utenti a M
ruoli; gli utenti membri ereditano i permessi UNION-ati con quelli
direttamente assegnati via ``user_roles``. Vedi
:func:`llm_wiki.db.roles.get_user_permissions` per l'aggregazione
effettiva.

Pattern allineato a :mod:`llm_wiki.db.roles`: psycopg3 + dict_row,
``rollback()`` su read-only.

Layout interno (cap 500 LOC per file):

- ``crud`` — list/get/create/update/delete + formatting.
- ``members`` — membership ops + ``get_user_groups`` per ``/api/auth/me``.
- ``roles`` — role assignment + tenant compatibility check.

Tutto re-esportato qui per import path stabile (``from
llm_wiki.db.groups import create_group, ...``).
"""

from __future__ import annotations

from llm_wiki.db.groups.crud import (
    CrossTenantError,
    GroupNotFoundError,
    SystemGroupProtected,
    create_group,
    delete_group,
    get_group_by_id,
    list_groups,
    update_group,
)
from llm_wiki.db.groups.members import (
    add_member,
    add_members_bulk,
    get_group_members,
    get_user_groups,
    remove_member,
)
from llm_wiki.db.groups.roles import (
    assign_role,
    get_group_roles,
    revoke_role,
)

__all__ = [
    # exceptions
    "CrossTenantError",
    "GroupNotFoundError",
    "SystemGroupProtected",
    # crud
    "list_groups",
    "get_group_by_id",
    "create_group",
    "update_group",
    "delete_group",
    # members
    "add_member",
    "add_members_bulk",
    "remove_member",
    "get_group_members",
    "get_user_groups",
    # roles
    "assign_role",
    "revoke_role",
    "get_group_roles",
]
