"""CVE Hunter Swarm Handlers.

Modular handlers for coordinator functionality:
- SASTToolsHandler: Semgrep, CodeQL integration
- DASTToolsHandler: OWASP ZAP integration
- FindingsHandler: Finding normalization and processing
- CorrelationsHandler: CVE and attack pattern correlations
- EventsHandler: Event subscription and handling
- FeedbackHandler: Feedback recording and learning
- ReportingHandler: Report generation
"""

from .correlations import CorrelationsHandler
from .dast_tools import DASTToolsHandler
from .events import EventsHandler
from .feedback import FeedbackHandler
from .findings import FindingsHandler
from .reporting import ReportingHandler
from .sast_tools import SASTToolsHandler
from .scanning import ScanningMixin
from .status import StatusMixin
from .analysis import AnalysisMixin

__all__ = [
    "CorrelationsHandler",
    "DASTToolsHandler",
    "EventsHandler",
    "FeedbackHandler",
    "FindingsHandler",
    "ReportingHandler",
    "SASTToolsHandler",
    "ScanningMixin",
    "StatusMixin",
    "AnalysisMixin",
]
