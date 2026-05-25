"""Seed a tenant with admin user + default policies (multi-tenant deploy).

Usage:
  uv run python scripts/seed_tenant.py --tenant acme --email admin@acme.local
"""

from __future__ import annotations
import argparse
import asyncio
import getpass
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docheck-engine" / "src"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402

from docheck.core.config import settings  # noqa: E402
from docheck.core.security import hash_password  # noqa: E402
from docheck.core.tenant import set_tenant  # noqa: E402
from docheck.db.models import Base, User, UserRole, Role, Permission  # noqa: E402


SEED_PERMS = [
    ("admin", "document", "read"),
    ("admin", "document", "write"),
    ("admin", "policy", "read"),
    ("admin", "policy", "write"),
    ("admin", "report", "read"),
    ("admin", "report", "export"),
    ("admin", "audit", "read"),
]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--email", required=True)
    args = ap.parse_args()

    pw = getpass.getpass("Password (>=12 chars): ")
    if len(pw) < 12:
        sys.exit("Password too short")

    set_tenant(args.tenant)
    eng = create_async_engine(f"sqlite+aiosqlite:///{settings.db_path}")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(eng, expire_on_commit=False)() as db:
        # Roles & permissions (idempotent on conflict-skip via try/except)
        try:
            db.add(Role(id="admin", label="Administrator"))
            await db.flush()
        except Exception:
            await db.rollback()

        for role, resource, action in SEED_PERMS:
            try:
                db.add(Permission(role_id=role, resource=resource, action=action))
                await db.flush()
            except Exception:
                await db.rollback()

        uid = f"u-{uuid.uuid4().hex[:12]}"
        db.add(
            User(
                id=uid,
                tenant_id=args.tenant,
                email=args.email,
                display_name=args.email.split("@")[0],
                pw_hash=hash_password(pw),
            )
        )
        db.add(UserRole(user_id=uid, role_id="admin"))
        await db.commit()

        print(f"Tenant '{args.tenant}' seeded:")
        print(f"  user_id: {uid}")
        print(f"  email:   {args.email}")
        print("  role:    admin")


if __name__ == "__main__":
    asyncio.run(main())
