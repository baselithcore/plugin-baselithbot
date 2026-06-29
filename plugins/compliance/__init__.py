"""Compliance (GRC) console plugin — NIS2, DORA, GDPR, and the EU AI Act.

A single governance surface over the framework's compliance primitives. It owns
no domain data: every tab is a console over a Sacred-Core subsystem —

* :mod:`core.incidents`    — NIS2 Art. 23 + DORA Art. 19 incident reporting.
* :mod:`core.privacy`      — GDPR data-subject requests (access / erasure / retention).
* :mod:`core.thirdparty`   — DORA Art. 28 Register of Information.
* :mod:`core.transparency` — EU AI Act Art. 50 disclosure / provenance.

The package is split into cohesive modules so no file approaches the 500 LOC cap:

* :mod:`config`  — typed settings (env-overridable, self-contained defaults).
* :mod:`i18n`    — backend locale negotiation (en default, it).
* :mod:`router`  — the async FastAPI surface, one sub-router per regulation.
* :mod:`plugin`  — the :class:`RouterPlugin` entry point + SPA mount.

It is a **system** plugin (admin-only nav). ``core/`` is never modified (Sacred
Core); only framework primitives are imported.
"""

from __future__ import annotations

from .plugin import CompliancePlugin, create_plugin

__all__ = ["CompliancePlugin", "create_plugin"]
