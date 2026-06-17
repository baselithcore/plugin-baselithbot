"""ReportRenderer core — composes mixins."""

from ._render_helpers import RenderHelpersMixin
from ._render_markdown import RenderMarkdownMixin


class ReportRenderer(RenderMarkdownMixin, RenderHelpersMixin):
    """Renders reports into final formats with research focus."""
