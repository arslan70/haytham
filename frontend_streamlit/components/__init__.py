"""UI components for the Streamlit prototype.

This module provides reusable UI components:
- feedback_chat: Chat panel for post-workflow feedback
- results_panel: Collapsible display of workflow results
- styling: Design system utilities and styled components
"""

from frontend_streamlit.components.feedback_chat import render_feedback_chat
from frontend_streamlit.components.results_panel import render_results_panel
from frontend_streamlit.components.styling import (
    HaythamColors,
    footer_trust_indicator,
    header_with_branding,
    info_card,
    load_css,
    nav_item,
    step_indicator,
    workspace_card,
)

__all__ = [
    "render_feedback_chat",
    "render_results_panel",
    # Styling utilities
    "load_css",
    "workspace_card",
    "step_indicator",
    "header_with_branding",
    "nav_item",
    "info_card",
    "footer_trust_indicator",
    "HaythamColors",
]
