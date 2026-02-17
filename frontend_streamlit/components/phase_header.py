"""Phase Context Header - Shows phase name, question, agent role, and sub-page indicators.

Displays contextual information at the top of each view so users understand
where they are in the Genesis workflow.
"""

import streamlit as st

# Phase configuration
PHASE_CONFIG = {
    "why": {
        "number": 1,
        "name": "WHY",
        "question": "Is this idea worth pursuing?",
        "role": "Business Analyst",
        "color": "#1f77b4",
    },
    "what": {
        "number": 2,
        "name": "WHAT",
        "question": "What should we build first?",
        "role": "Product Manager",
        "color": "#2ca02c",
    },
    "how": {
        "number": 3,
        "name": "HOW",
        "question": "How should we build each capability?",
        "role": "Software Architect",
        "color": "#6B2D8B",
    },
    "stories": {
        "number": 4,
        "name": "STORIES",
        "question": "What are the implementation tasks?",
        "role": "Project Manager",
        "color": "#d62728",
    },
}


def render_phase_header(
    phase_key: str,
    sub_pages: list[str] | None = None,
    current_sub_page: str | None = None,
) -> None:
    """Render the phase context header.

    Args:
        phase_key: One of 'why', 'what', 'how', 'stories'
        sub_pages: Optional list of sub-page names for phases with multiple views
        current_sub_page: Which sub-page is currently active
    """
    config = PHASE_CONFIG.get(phase_key)
    if not config:
        return

    color = config["color"]

    # Sub-page tabs (visual only)
    sub_page_html = ""
    if sub_pages and current_sub_page:
        tabs = []
        for page in sub_pages:
            if page == current_sub_page:
                tabs.append(
                    f'<span style="font-size: 12px; color: {color}; font-weight: 600; '
                    f'border-bottom: 2px solid {color}; padding-bottom: 2px;">{page}</span>'
                )
            else:
                tabs.append(f'<span style="font-size: 12px; color: #999;">{page}</span>')
        sub_page_html = (
            '<div style="display: flex; gap: 16px; margin-top: 8px;">' + "".join(tabs) + "</div>"
        )

    header_html = (
        f'<div style="background: linear-gradient(135deg, {color}10, {color}05); border-left: 3px solid {color}; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 16px;">'
        f'<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">'
        f'<span style="font-size: 11px; font-weight: 700; color: {color}; text-transform: uppercase; letter-spacing: 1px; background: {color}18; padding: 2px 8px; border-radius: 4px;">Phase {config["number"]}: {config["name"]}</span>'
        f'<span style="font-size: 11px; color: #999;">|</span>'
        f'<span style="font-size: 11px; color: #888;">{config["role"]}</span>'
        f"</div>"
        f'<div style="font-size: 14px; color: #555; font-style: italic;">{config["question"]}</div>'
        f"{sub_page_html}"
        f"</div>"
    )
    st.markdown(header_html, unsafe_allow_html=True)
