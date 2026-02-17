"""Genesis Progress Bar - Horizontal phase progress indicator.

Renders WHY -> WHAT -> HOW -> STORIES with BUILD/VALIDATE as Coming Soon placeholders.
Status per phase derived from lock files and stage output existence.
"""

from lib.session_utils import get_session_dir, setup_paths

setup_paths()

import streamlit as st  # noqa: E402

SESSION_DIR = get_session_dir()

# Phase definitions: (key, label, workflow_types_to_check, stage_slugs_for_output)
PHASES = [
    {
        "key": "why",
        "label": "WHY",
        "subtitle": "Validate",
        "lock_workflow": "idea-validation",
        "output_stages": ["validation-summary", "risk-assessment"],
    },
    {
        "key": "what",
        "label": "WHAT",
        "subtitle": "Specify",
        "lock_workflow": "mvp-specification",
        "output_stages": ["capability-model"],
    },
    {
        "key": "how",
        "label": "HOW",
        "subtitle": "Design",
        "lock_workflow": "architecture-decisions",
        "output_stages": ["build-buy-analysis", "architecture-decisions"],
    },
    {
        "key": "stories",
        "label": "STORIES",
        "subtitle": "Plan",
        "lock_workflow": "story-generation",
        "output_stages": ["story-generation"],
    },
]

PLACEHOLDER_PHASES = [
    {"key": "build", "label": "BUILD", "subtitle": "Coming Soon"},
    {"key": "validate", "label": "VALIDATE", "subtitle": "Coming Soon"},
]

METADATA_FILES = {"checkpoint.md", "user_feedback.md"}


def _is_locked(workflow_type: str) -> bool:
    lock_file = SESSION_DIR / f".{workflow_type}.locked"
    return lock_file.exists()


def _has_output(stage_slug: str) -> bool:
    stage_dir = SESSION_DIR / stage_slug
    if not stage_dir.exists():
        return False
    for f in stage_dir.glob("*.md"):
        if f.name not in METADATA_FILES and f.stat().st_size > 100:
            return True
    return False


def _get_phase_status(phase: dict) -> str:
    """Return phase status: 'complete', 'in_progress', 'not_started'."""
    if _is_locked(phase["lock_workflow"]):
        return "complete"
    if any(_has_output(s) for s in phase["output_stages"]):
        return "in_progress"
    return "not_started"


def render_genesis_progress() -> None:
    """Render the Genesis progress bar showing WHY -> WHAT -> HOW -> STORIES."""
    phase_statuses = []
    for phase in PHASES:
        status = _get_phase_status(phase)
        phase_statuses.append((phase, status))

    # Count completed for overall progress
    completed = sum(1 for _, s in phase_statuses if s == "complete")
    total = len(PHASES)

    # Build HTML — no leading whitespace to avoid Streamlit code-block rendering
    phase_items_html = ""
    for i, (phase, status) in enumerate(phase_statuses):
        if status == "complete":
            icon = '<span style="color: #4CAF50; font-size: 14px;">&#9679;</span>'
            label_color = "#4CAF50"
            subtitle_color = "#666"
        elif status == "in_progress":
            icon = '<span style="color: #2196F3; font-size: 14px;">&#9684;</span>'
            label_color = "#2196F3"
            subtitle_color = "#666"
        else:
            icon = '<span style="color: #ccc; font-size: 14px;">&#9675;</span>'
            label_color = "#999"
            subtitle_color = "#bbb"

        connector = ""
        if i < len(PHASES) - 1:
            line_color = "#4CAF50" if status == "complete" else "#ddd"
            connector = f'<div style="flex: 1; height: 2px; background: {line_color}; margin: 0 4px;"></div>'

        phase_items_html += (
            f'<div style="display: flex; flex-direction: column; align-items: center; min-width: 60px;">'
            f"{icon}"
            f'<span style="font-size: 12px; font-weight: 600; color: {label_color}; margin-top: 4px;">{phase["label"]}</span>'
            f'<span style="font-size: 10px; color: {subtitle_color};">{phase["subtitle"]}</span>'
            f"</div>"
            f"{connector}"
        )

    # Add placeholder phases
    for placeholder in PLACEHOLDER_PHASES:
        phase_items_html += (
            f'<div style="flex: 1; height: 2px; background: #eee; margin: 0 4px;"></div>'
            f'<div style="display: flex; flex-direction: column; align-items: center; min-width: 60px; opacity: 0.5;">'
            f'<span style="color: #ccc; font-size: 14px;">&#8212;</span>'
            f'<span style="font-size: 12px; font-weight: 600; color: #ccc; margin-top: 4px;">{placeholder["label"]}</span>'
            f'<span style="font-size: 10px; color: #ddd;">{placeholder["subtitle"]}</span>'
            f"</div>"
        )

    card_html = (
        f'<div style="background: #fafafa; border: 1px solid #eee; border-radius: 8px; padding: 16px 24px; margin-bottom: 16px;">'
        f'<div style="display: flex; align-items: center; margin-bottom: 8px;">'
        f'<span style="font-size: 12px; font-weight: 600; color: #6B2D8B; text-transform: uppercase; letter-spacing: 1px;">Genesis Progress</span>'
        f'<span style="font-size: 11px; color: #999; margin-left: auto;">{completed}/{total} phases complete</span>'
        f"</div>"
        f'<div style="display: flex; align-items: center; justify-content: center;">'
        f"{phase_items_html}"
        f"</div>"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)
