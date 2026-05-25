"""`.env` lock + atomic write + key/value upsert primitives."""

from __future__ import annotations

import contextlib
import errno
import logging
import os as _os
import re
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

try:
    import fcntl as _fcntl  # POSIX only; Windows wizard runs single-process anyway
except ImportError:  # pragma: no cover — Windows
    _fcntl = None  # type: ignore[assignment]

from llm_wiki.admin.scaffold.models import ScaffoldError

logger = logging.getLogger(__name__)

_ENV_VALUE_FORBIDDEN = re.compile(r"[\r\n\x00]")


@contextlib.contextmanager
def _env_lock(env_path: Path) -> Iterator[None]:
    """Advisory ``fcntl.flock`` on a sidecar lockfile next to ``.env``.

    Both :func:`scaffold_pack` and ``activate_tenant`` perform a
    read-modify-write on the same ``.env`` — without a lock, two
    concurrent wizard requests can interleave and silently drop one
    side's keys. The lockfile is a sidecar (``.env.lock``) so the
    atomic ``os.replace`` on ``.env`` itself doesn't invalidate the lock
    inode. No-op on platforms without ``fcntl`` (Windows): the wizard
    is single-machine and serialised by the loopback gate anyway.
    """
    if _fcntl is None:
        yield
        return
    lock_path = env_path.parent / (env_path.name + ".lock")
    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    fd = _os.open(str(lock_path), _os.O_RDWR | _os.O_CREAT, 0o600)
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        yield
    finally:
        try:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
        finally:
            _os.close(fd)


def _atomic_write_env(env_path: Path, content: str) -> None:
    """Write ``content`` to ``env_path`` atomically with 0600 perms.

    Caller must hold :func:`_env_lock`. The temp file lives in the same
    directory so ``os.replace`` is a same-filesystem rename. On any
    failure the temp file is cleaned up.
    """
    parent = env_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=str(parent))
    tmp_path = Path(tmp_name)
    try:
        with _os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        try:
            _os.chmod(tmp_path, 0o600)
        except OSError as exc:
            logger.warning("[scaffold] chmod 0600 failed on %s: %s", tmp_path, exc)
        _os.replace(tmp_path, env_path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                logger.warning("[scaffold] tempfile cleanup failed: %s", exc)
        raise


def mutate_env_file(
    env_path: Path,
    mutator: Callable[[str], str],
    *,
    template: Path | None = None,
) -> bool:
    """Read-modify-write ``env_path`` under an exclusive lock.

    ``mutator`` receives the current content (or template/empty if the
    file is missing) and must return the new content. Returns ``True``
    on successful write, ``False`` on permission errors so the caller
    can degrade to manual instructions.
    """
    with _env_lock(env_path):
        base = ""
        if env_path.exists():
            try:
                base = env_path.read_text(encoding="utf-8")
            except OSError:
                return False
        elif template is not None and template.exists():
            try:
                base = template.read_text(encoding="utf-8")
            except OSError:
                base = ""
        new_content = mutator(base)
        try:
            _atomic_write_env(env_path, new_content)
        except OSError:
            return False
    return True


def _upsert_env_kv(text: str, key: str, value: str) -> str:
    # Hardening: blocca newline/CR/NUL nel valore. Senza questo controllo
    # un valore tipo `sk-foo\nADMIN_API_LOOPBACK_ONLY=false` aggiunge
    # righe arbitrarie al .env e ribalta la security posture al prossimo
    # boot. Validato qui (single chokepoint) invece che in ogni call site.
    if _ENV_VALUE_FORBIDDEN.search(value):
        raise ScaffoldError(
            f".env value for {key!r} contains forbidden control characters (newline / CR / NUL)"
        )
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(f"{key}={value}", text, count=1)
    suffix = "" if (text.endswith("\n") or not text) else "\n"
    return text + suffix + f"{key}={value}\n"
