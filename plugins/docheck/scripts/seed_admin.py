"""Create or update initial admin user. Idempotent."""

from __future__ import annotations
import asyncio
import getpass
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docheck-engine" / "src"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402

from docheck.core.config import settings  # noqa: E402
from docheck.core.security import hash_password  # noqa: E402
from docheck.db.models import Role, User, UserRole  # noqa: E402


async def main() -> None:
    email = input("Admin email: ").strip()
    if not email:
        sys.exit("Email required")
    pw = getpass.getpass("Password (>=12 chars): ")
    if len(pw) < 12:
        sys.exit("Password >= 12 chars required")

    eng = create_async_engine(f"sqlite+aiosqlite:///{settings.db_path}")
    async with async_sessionmaker(eng, expire_on_commit=False)() as db:
        # Ensure role exists
        if await db.get(Role, "admin") is None:
            db.add(Role(id="admin", label="Administrator"))
            await db.commit()

        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

        if existing:
            existing.pw_hash = hash_password(pw)
            existing.disabled_at = None
            user_id = existing.id
            action = "Updated"
        else:
            user_id = f"u-{uuid.uuid4().hex[:12]}"
            db.add(
                User(
                    id=user_id,
                    email=email,
                    display_name=email.split("@")[0],
                    pw_hash=hash_password(pw),
                )
            )
            action = "Created"

        # Ensure role binding
        existing_role = await db.get(UserRole, (user_id, "admin"))
        if existing_role is None:
            db.add(UserRole(user_id=user_id, role_id="admin"))

        await db.commit()
        print(f"{action} admin user: {email} (id={user_id})")


if __name__ == "__main__":
    asyncio.run(main())
