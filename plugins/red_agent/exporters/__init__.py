"""Finding exporters for downstream SIEM/SOAR/GRC ingestion.

Currently shipped:

* :func:`to_ocsf` — Open Cybersecurity Schema Framework 1.4 (OCSF
  Vulnerability Finding, ``class_uid=2002``).

The legacy SARIF 2.1.0 exporter still lives at
:mod:`plugins.red_agent.sarif` for code-scanning tools that consume the
SARIF feed natively.
"""

from __future__ import annotations

from plugins.red_agent.exporters.ocsf import to_ocsf, to_ocsf_event
from plugins.red_agent.exporters.sigma import to_sigma_dict, to_sigma_yaml

__all__ = ["to_ocsf", "to_ocsf_event", "to_sigma_dict", "to_sigma_yaml"]
