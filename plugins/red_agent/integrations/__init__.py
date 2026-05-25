"""SOAR / ticketing integrations for the Red Agent.

Outbound: notify a downstream SIEM/SOAR/ticketing system every time a
new finding above the configured severity floor is persisted, using a
provider-agnostic OCSF-shaped payload signed with HMAC-SHA256.

Inbound (future): receive ``state`` updates from the downstream system
(ticket closed, accepted as risk, …) via webhook + signature
verification, and apply them through ``RedAgentPersistence.update_finding_triage``.
"""

from __future__ import annotations

from plugins.red_agent.integrations.autopr import (
    AutoRemediationService,
    RemediationResult,
    UnsupportedRemediation,
)
from plugins.red_agent.integrations.webhook import WebhookNotifier
from plugins.red_agent.integrations.webhook_receiver import (
    WebhookEvent,
    WebhookReceiver,
    WebhookSignatureInvalid,
)

__all__ = [
    "AutoRemediationService",
    "RemediationResult",
    "UnsupportedRemediation",
    "WebhookEvent",
    "WebhookNotifier",
    "WebhookReceiver",
    "WebhookSignatureInvalid",
]
