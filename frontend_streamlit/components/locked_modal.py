"""Locked Phase Modal - Explains why a phase is locked and what to do.

Shows why a phase is locked, a dependency checklist, and a button to go
to the current active phase.
"""

import streamlit as st

# Which workflow must be locked before each phase becomes available
PHASE_DEPENDENCIES = {
    "what": {
        "label": "MVP Specification",
        "requires": "idea-validation",
        "requires_label": "Idea Validation",
        "message": "Complete and accept Idea Validation before defining your MVP scope.",
    },
    "how": {
        "label": "Technical Design",
        "requires": "mvp-specification",
        "requires_label": "MVP Specification",
        "message": "Complete and accept MVP Specification before designing technical architecture.",
    },
    "stories": {
        "label": "Story Generation",
        "requires": "architecture-decisions",
        "requires_label": "Architecture Decisions",
        "message": "Complete and accept Architecture Decisions before generating stories.",
    },
}


def render_locked_explanation(
    phase_key: str,
    navigate_to: str | None = None,
) -> None:
    """Render an explanation for why a phase is locked.

    Args:
        phase_key: One of 'what', 'how', 'stories'
        navigate_to: Optional page to navigate to
    """
    dep = PHASE_DEPENDENCIES.get(phase_key)
    if not dep:
        return

    st.warning(f"**{dep['label']}** is locked")
    st.markdown(dep["message"])
    st.markdown(f"**Required:** Accept _{dep['requires_label']}_ to unlock this phase.")

    if navigate_to:
        if st.button(
            f"Go to {dep['requires_label']}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.navigate_to = navigate_to
            st.rerun()
