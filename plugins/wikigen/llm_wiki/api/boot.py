"""Per-process boot identity.

Materialised once at import time. The frontend's setup wizard captures
``BOOT_ID`` BEFORE triggering a restart and waits for ``/api/branding``
to report a different value — proves the worker actually rebooted (not
just the same process returning the new tenant after ``os.environ`` was
mutated in-place).
"""

from __future__ import annotations

import secrets
import time

BOOT_ID = secrets.token_hex(8)
BOOT_AT = time.time()
