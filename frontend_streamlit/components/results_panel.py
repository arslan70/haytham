"""Results panel component for displaying workflow outputs.

This component displays workflow stage outputs in collapsible expanders,
allowing users to review results before providing feedback or accepting.
"""

from pathlib import Path

import streamlit as st


def render_results_panel(
    session_dir: Path,
    stage_slugs: list[str],
    stage_display_names: dict[str, str] | None = None,
    expanded_stage: str | None = None,
) -> None:
    """Render workflow results in collapsible panels.

    Displays each stage's output in an expander, with the last stage
    expanded by default to show the most recent results.

    Args:
        session_dir: Path to the session directory
        stage_slugs: Ordered list of stage slugs to display
        stage_display_names: Optional mapping of slug to display name
        expanded_stage: Stage slug to expand by default (last stage if None)
    """
    if not stage_slugs:
        st.info("No results to display.")
        return

    # Default to expanding the last stage
    if expanded_stage is None:
        expanded_stage = stage_slugs[-1]

    # Default display names if not provided
    if stage_display_names is None:
        stage_display_names = {slug: slug.replace("-", " ").title() for slug in stage_slugs}

    st.subheader("Workflow Results")

    for slug in stage_slugs:
        display_name = stage_display_names.get(slug, slug)
        stage_dir = session_dir / slug

        # Check if stage has outputs
        if not stage_dir.exists():
            with st.expander(f"{display_name} (no output)", expanded=False):
                st.caption("This stage has not been executed yet.")
            continue

        # Load and display outputs
        output_content = _load_stage_output(stage_dir)

        if output_content:
            is_expanded = slug == expanded_stage
            with st.expander(display_name, expanded=is_expanded):
                st.markdown(output_content)
        else:
            with st.expander(f"{display_name} (empty)", expanded=False):
                st.caption("This stage produced no output.")


def _load_stage_output(stage_dir: Path) -> str | None:
    """Load combined output from all agent files in a stage directory.

    Args:
        stage_dir: Path to the stage directory

    Returns:
        Combined markdown content, or None if no outputs found
    """
    outputs = []

    # Look for markdown files (excluding checkpoint and feedback files)
    for md_file in sorted(stage_dir.glob("*.md")):
        if md_file.name in ("checkpoint.md", "user_feedback.md"):
            continue

        try:
            content = md_file.read_text()
            # Strip output header if present
            if content.startswith("## Output"):
                content = content[len("## Output") :].strip()
            outputs.append(content)
        except Exception:
            continue

    return "\n\n---\n\n".join(outputs) if outputs else None


def render_stage_output(
    session_dir: Path,
    stage_slug: str,
    display_name: str | None = None,
) -> None:
    """Render a single stage's output.

    Useful for showing individual stage results without the full panel.

    Args:
        session_dir: Path to the session directory
        stage_slug: Stage slug to display
        display_name: Optional display name for the stage
    """
    if display_name is None:
        display_name = stage_slug.replace("-", " ").title()

    stage_dir = session_dir / stage_slug

    if not stage_dir.exists():
        st.warning(f"{display_name}: No output available.")
        return

    output_content = _load_stage_output(stage_dir)

    if output_content:
        st.markdown(f"### {display_name}")
        st.markdown(output_content)
    else:
        st.warning(f"{display_name}: Empty output.")


def get_stage_outputs_for_workflow(
    session_dir: Path,
    workflow_type: str,
) -> dict[str, str]:
    """Get all stage outputs for a workflow type.

    Args:
        session_dir: Path to the session directory
        workflow_type: Type of workflow (idea-validation, mvp-specification, etc.)

    Returns:
        Dict mapping stage slug to output content
    """
    # Define stages per workflow type
    workflow_stages = {
        "idea-validation": [
            "idea-analysis",
            "market-context",
            "risk-assessment",
            "validation-summary",
        ],
        "mvp-specification": [
            "mvp-scope",
            "capability-model",
        ],
        "story-generation": [
            "architecture-decisions",
            "component-boundaries",
            "story-generation",
            "story-validation",
            "dependency-ordering",
        ],
    }

    stage_slugs = workflow_stages.get(workflow_type, [])
    outputs = {}

    for slug in stage_slugs:
        stage_dir = session_dir / slug
        if stage_dir.exists():
            content = _load_stage_output(stage_dir)
            if content:
                outputs[slug] = content

    return outputs
