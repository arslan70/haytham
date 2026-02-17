"""Feedback chat component for post-workflow user feedback.

This component provides a chat-like interface for users to provide feedback
after a workflow completes. It includes:
- Text input for feedback
- "Accept & Continue" button to lock the workflow and proceed
- Processing state indicator
- Example prompts to guide users
"""

from collections.abc import Callable

import streamlit as st


def render_feedback_chat(
    on_feedback_submit: Callable[[str], None],
    on_accept: Callable[[], None],
    workflow_name: str = "workflow",
    is_processing: bool = False,
    feedback_key: str = "feedback_input",
) -> None:
    """Render the feedback chat panel.

    This component displays a text area for feedback input and buttons
    for submitting feedback or accepting results.

    Args:
        on_feedback_submit: Callback when user submits feedback
        on_accept: Callback when user accepts and continues
        workflow_name: Display name of the workflow (e.g., "Idea Validation")
        is_processing: If True, shows processing state and disables inputs
        feedback_key: Session state key for the feedback input
    """
    st.subheader("Review & Feedback")

    # Help text
    st.caption(
        f"Review the **{workflow_name}** results below. "
        "Provide feedback to refine the outputs, or accept to lock and continue."
    )

    if is_processing:
        # Processing state - show spinner and disable inputs
        st.info("Processing your feedback... This may take a moment if research is needed.")
        st.spinner("Working on revisions...")
        return

    # Feedback input
    feedback = st.text_area(
        "Your feedback (optional)",
        placeholder=(
            "Examples:\n"
            "- 'Add payment integration to the MVP'\n"
            "- 'Remove social features'\n"
            "- 'Research competitor Stripe and add comparison'\n"
            "- 'Focus more on B2B market segment'"
        ),
        key=feedback_key,
        height=150,
        help="Describe changes you'd like to make. Be specific about what to add, remove, or modify.",
    )

    # Buttons
    col1, col2 = st.columns(2)

    with col1:
        submit_disabled = not feedback or not feedback.strip()
        if st.button(
            "Submit Feedback",
            disabled=submit_disabled,
            use_container_width=True,
            type="secondary",
        ):
            on_feedback_submit(feedback.strip())

    with col2:
        if st.button(
            "Accept & Continue",
            type="primary",
            use_container_width=True,
        ):
            on_accept()

    # Warning about locking
    st.caption(
        "Accepting will lock this workflow's outputs. You won't be able to modify them later."
    )


def render_feedback_status(
    affected_stages: list[str],
    revised_stages: list[str],
    reasoning: str,
) -> None:
    """Render the feedback processing status.

    Shows which stages were affected and revised after feedback processing.

    Args:
        affected_stages: Stages directly affected by feedback
        revised_stages: All stages that were revised (including cascade)
        reasoning: Router's reasoning for stage selection
    """
    st.success("Feedback processed successfully!")

    # Show what was affected
    if affected_stages:
        st.write("**Stages affected by your feedback:**")
        for stage in affected_stages:
            st.write(f"- {stage}")

    if revised_stages and len(revised_stages) > len(affected_stages):
        cascaded = [s for s in revised_stages if s not in affected_stages]
        if cascaded:
            st.write("**Downstream stages also updated:**")
            for stage in cascaded:
                st.write(f"- {stage}")

    if reasoning:
        with st.expander("Why these stages?"):
            st.write(reasoning)


def render_processing_progress(
    current_stage: str | None,
    total_stages: int,
    completed_stages: list[str],
) -> None:
    """Render progress during feedback processing.

    Shows a progress indicator while stages are being revised.

    Args:
        current_stage: Stage currently being revised (None if done)
        total_stages: Total number of stages to revise
        completed_stages: List of stages already revised
    """
    if total_stages == 0:
        return

    progress = len(completed_stages) / total_stages
    st.progress(progress, text=f"Revising: {current_stage or 'Complete'}")

    # Show completed stages
    if completed_stages:
        with st.expander("Completed revisions", expanded=False):
            for stage in completed_stages:
                st.write(f"- {stage}")
