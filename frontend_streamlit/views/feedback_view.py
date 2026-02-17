"""Feedback View - Post-workflow feedback phase.

This view is displayed after a workflow completes, allowing users to:
1. Review the workflow results
2. Provide feedback to refine outputs
3. Accept and lock the workflow to continue

The view uses a two-column layout:
- Left column: Results panel with collapsible stage outputs
- Right column: Feedback chat for user input

This is not a standalone page - it's meant to be integrated into the
execution flow or called as a component from other views.
"""

import sys
from pathlib import Path

from lib.session_utils import get_session_dir, get_system_goal, load_environment, setup_paths

setup_paths()
load_environment()

import streamlit as st  # noqa: E402

# Workflow stage configurations
WORKFLOW_CONFIGS = {
    "idea-validation": {
        "display_name": "Idea Validation",
        "stages": [
            ("idea-analysis", "Idea Analysis"),
            ("market-context", "Market Context"),
            ("risk-assessment", "Risk Assessment"),
            ("validation-summary", "Validation Summary"),
        ],
        "next_page": "views/discovery.py",
    },
    "mvp-specification": {
        "display_name": "MVP Specification",
        "stages": [
            ("mvp-scope", "MVP Scope"),
            ("capability-model", "Capability Model"),
        ],
        "next_page": "views/mvp_spec.py",
    },
    "story-generation": {
        "display_name": "Story Generation",
        "stages": [
            ("architecture-decisions", "Architecture Decisions"),
            ("component-boundaries", "Component Boundaries"),
            ("story-generation", "Story Generation"),
            ("story-validation", "Story Validation"),
            ("dependency-ordering", "Dependency Ordering"),
        ],
        "next_page": "views/stories.py",
    },
}


def render_feedback_view(workflow_type: str) -> None:
    """Render the complete feedback view for a workflow.

    This is the main entry point for the feedback phase. It handles:
    - Displaying results and feedback input
    - Processing feedback submissions
    - Locking workflow on acceptance
    - Navigation to next step

    Args:
        workflow_type: Type of workflow (idea-validation, mvp-specification, etc.)
    """
    config = WORKFLOW_CONFIGS.get(workflow_type)
    if not config:
        st.error(f"Unknown workflow type: {workflow_type}")
        return

    session_dir = get_session_dir()
    system_goal = get_system_goal()

    # Initialize session state for feedback phase
    if "feedback_processing" not in st.session_state:
        st.session_state.feedback_processing = False
    if "feedback_result" not in st.session_state:
        st.session_state.feedback_result = None
    if "pending_feedback" not in st.session_state:
        st.session_state.pending_feedback = None

    # Process pending feedback if we're in processing mode
    if st.session_state.feedback_processing and st.session_state.pending_feedback:
        pending = st.session_state.pending_feedback
        st.session_state.pending_feedback = None  # Clear pending

        # Show processing indicator
        with st.spinner(f"Processing feedback for {config['display_name']}..."):
            _process_feedback(
                feedback=pending,
                workflow_type=workflow_type,
                config=config,
                session_dir=session_dir,
                system_goal=system_goal,
            )
        # Rerun to show results
        st.rerun()

    # Title
    st.title(f"Review: {config['display_name']}")
    if system_goal:
        st.caption(f"*{system_goal}*")

    st.divider()

    # Two-column layout: Results (2/3) | Feedback (1/3)
    results_col, feedback_col = st.columns([2, 1])

    # Results panel (left column)
    with results_col:
        _render_results_section(session_dir, config)

    # Feedback panel (right column)
    with feedback_col:
        _render_feedback_section(
            workflow_type=workflow_type,
            config=config,
            session_dir=session_dir,
            system_goal=system_goal,
        )


def _render_results_section(session_dir: Path, config: dict) -> None:
    """Render the results section with collapsible outputs."""
    from components.results_panel import render_results_panel

    stage_slugs = [slug for slug, _ in config["stages"]]
    stage_names = dict(config["stages"])

    render_results_panel(
        session_dir=session_dir,
        stage_slugs=stage_slugs,
        stage_display_names=stage_names,
    )


def _render_feedback_section(
    workflow_type: str,
    config: dict,
    session_dir: Path,
    system_goal: str | None,
) -> None:
    """Render the feedback section with chat input and buttons."""
    from components.feedback_chat import (
        render_feedback_chat,
        render_feedback_status,
    )

    # Show previous feedback result if any
    if st.session_state.feedback_result:
        result = st.session_state.feedback_result
        render_feedback_status(
            affected_stages=result.affected_stages,
            revised_stages=result.revised_stages,
            reasoning=result.reasoning,
        )
        st.divider()
        # Clear result after showing
        st.session_state.feedback_result = None

    # Render feedback chat
    render_feedback_chat(
        on_feedback_submit=lambda fb: _handle_feedback_submit(
            feedback=fb,
            workflow_type=workflow_type,
            config=config,
            session_dir=session_dir,
            system_goal=system_goal,
        ),
        on_accept=lambda: _handle_accept(workflow_type, config, session_dir),
        workflow_name=config["display_name"],
        is_processing=st.session_state.feedback_processing,
    )


def _handle_feedback_submit(
    feedback: str,
    workflow_type: str,
    config: dict,
    session_dir: Path,
    system_goal: str | None,
) -> None:
    """Handle feedback submission.

    Stores the feedback and triggers a rerun to start processing.
    The actual processing happens in render_feedback_view after rerun.
    """
    st.session_state.feedback_processing = True
    st.session_state.pending_feedback = feedback
    st.rerun()


def _process_feedback(
    feedback: str,
    workflow_type: str,
    config: dict,
    session_dir: Path,
    system_goal: str | None,
):
    """Process feedback using the FeedbackProcessor.

    This is called when feedback_processing is True.
    """
    try:
        from haytham.feedback.feedback_processor import FeedbackProcessor
        from haytham.session.session_manager import SessionManager

        # Get stage slugs for the workflow
        stage_slugs = [slug for slug, _ in config["stages"]]

        # Create session manager
        base_dir = session_dir.parent
        session_manager = SessionManager(str(base_dir))

        # Create processor
        processor = FeedbackProcessor(
            session_manager=session_manager,
            workflow_type=workflow_type,
            workflow_stages=stage_slugs,
            system_goal=system_goal or "",
        )

        # Process feedback
        result = processor.process_feedback(feedback=feedback)

        # Store result for display
        st.session_state.feedback_result = result
        st.session_state.feedback_processing = False

        return result

    except Exception as e:
        st.session_state.feedback_processing = False
        st.error(f"Error processing feedback: {e}")
        return None


def _handle_accept(workflow_type: str, config: dict, session_dir: Path) -> None:
    """Handle accept and continue action.

    Locks the workflow and navigates to the next page.
    """
    try:
        from haytham.session.session_manager import SessionManager

        # Lock the workflow
        base_dir = session_dir.parent
        session_manager = SessionManager(str(base_dir))
        session_manager.lock_workflow(workflow_type)

        # Clear feedback state
        st.session_state.feedback_processing = False
        st.session_state.feedback_result = None

        # Clear feedback workflow trigger (set by execution.py)
        if "feedback_workflow" in st.session_state:
            del st.session_state.feedback_workflow

        # Show success and rerun to let Haytham.py rebuild navigation
        # (the next page may not be in navigation until workflow outputs exist)
        st.success(f"{config['display_name']} locked and saved!")
        st.rerun()

    except Exception as e:
        st.error(f"Error accepting workflow: {e}")


# =============================================================================
# Standalone page mode (for testing)
# =============================================================================

if __name__ == "__main__" or "feedback_view" in sys.modules.get("__main__", "").__file__:
    # Check which workflow to show feedback for
    workflow_type = st.session_state.get("feedback_workflow_type", "idea-validation")

    # Render the view
    render_feedback_view(workflow_type)
