"""Architecture Decisions View - Display architecture decisions for Phase 3b: HOW.

This is the view for the Architecture Decisions workflow (Phase 3b).
After accepting, the user can proceed to Story Generation (Phase 4).
"""

import re

from lib.session_utils import get_session_dir, load_environment, setup_paths

setup_paths()
load_environment()

import streamlit as st  # noqa: E402
import yaml  # noqa: E402
from components.decision_gate import render_decision_gate  # noqa: E402
from components.feedback_conversation import (  # noqa: E402
    render_feedback_conversation,
)

SESSION_DIR = get_session_dir()

# Workflow configuration
WORKFLOW_TYPE = "architecture-decisions"
WORKFLOW_DISPLAY_NAME = "Architecture Decisions"


def load_startup_idea() -> str | None:
    """Load startup idea from project.yaml."""
    project_file = SESSION_DIR / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return data.get("system_goal", "")
        except Exception:
            pass
    return None


# -----------------------------------------------------------------------------
# Stage Configuration
# -----------------------------------------------------------------------------

STAGES = [
    {
        "id": "architecture-decisions",
        "name": "Architecture Decisions",
        "description": "Technical architecture and component decisions",
        "output_file": "architecture_decisions.md",
        "renderer": "architecture",
    },
]

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def strip_output_header(content: str) -> str:
    """Strip the '## Output' or '# Output' header from content."""
    content = re.sub(r"^#+ Output\s*\n+", "", content, flags=re.MULTILINE)
    return content.strip()


def load_stage_output(stage_id: str, filename: str) -> str | None:
    """Load a stage output file and strip output header."""
    file_path = SESSION_DIR / stage_id / filename
    if file_path.exists():
        content = file_path.read_text()
        return strip_output_header(content)
    return None


def get_stage_status(stage_id: str) -> bool:
    """Check if a stage has been completed."""
    stage_dir = SESSION_DIR / stage_id
    return stage_dir.exists() and any(stage_dir.glob("*.md"))


def extract_json_from_markdown(content: str) -> dict | None:
    """Extract JSON from markdown code block."""
    from haytham.agents.output_utils import extract_json_from_text

    return extract_json_from_text(content)


def render_architecture_decisions(content: str):
    """Render architecture decisions in a user-friendly format."""
    data = extract_json_from_markdown(content)
    if not data:
        # Fall back to markdown rendering if no JSON found
        st.markdown(content)
        return

    # System Overview
    overview = data.get("overview", {})
    if overview:
        st.markdown(
            f"""
<div style="background-color: #f0e6f6; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #6B2D8B; margin-bottom: 1.5rem;">
    <h3 style="margin: 0 0 0.5rem 0; color: #6B2D8B;">{overview.get("system_name", "System Architecture")}</h3>
    <p style="margin: 0; color: #333;">{overview.get("architecture_style", "")}</p>
</div>
""",
            unsafe_allow_html=True,
        )

    # Decisions
    decisions = data.get("decisions", [])
    if decisions:
        st.markdown("### Architecture Decisions")
        st.caption(f"{len(decisions)} decisions documented")

        for dec in decisions:
            decision_id = dec.get("id", "DEC-?")
            title = dec.get("title", "Decision")
            status = dec.get("status", "proposed")

            with st.expander(f"**{decision_id}: {title}** ({status})", expanded=False):
                st.markdown(f"**Context:** {dec.get('context', '')}")
                st.markdown(f"**Decision:** {dec.get('decision', '')}")
                st.markdown(f"**Rationale:** {dec.get('rationale', '')}")

                consequences = dec.get("consequences", [])
                if consequences:
                    st.markdown("**Consequences:**")
                    for c in consequences:
                        st.markdown(f"- {c}")

                alternatives = dec.get("alternatives_considered", [])
                if alternatives:
                    st.markdown("**Alternatives Considered:**")
                    for alt in alternatives:
                        st.markdown(f"- {alt}")

    # Components
    components = data.get("components", [])
    if components:
        st.markdown("### Components")
        st.caption(f"{len(components)} components defined")

        for comp in components:
            name = comp.get("name", "Component")
            comp_type = comp.get("type", "service")

            with st.expander(f"**{name}** ({comp_type})", expanded=False):
                st.markdown(f"**Purpose:** {comp.get('purpose', '')}")
                st.markdown(f"**Technology:** {comp.get('technology', 'TBD')}")

                responsibilities = comp.get("responsibilities", [])
                if responsibilities:
                    st.markdown("**Responsibilities:**")
                    for r in responsibilities:
                        st.markdown(f"- {r}")

                interfaces = comp.get("interfaces", [])
                if interfaces:
                    st.markdown("**Interfaces:**")
                    for i in interfaces:
                        st.markdown(f"- {i}")

    # Integration Points
    integrations = data.get("integrations", [])
    if integrations:
        st.markdown("### External Integrations")
        st.caption(f"{len(integrations)} integrations planned")

        for integ in integrations:
            name = integ.get("service", "Service")
            purpose = integ.get("purpose", "")

            with st.expander(f"**{name}** - {purpose}", expanded=False):
                st.markdown(f"**Integration Pattern:** {integ.get('pattern', 'API')}")
                st.markdown(f"**Authentication:** {integ.get('auth', 'TBD')}")

                considerations = integ.get("considerations", [])
                if considerations:
                    st.markdown("**Considerations:**")
                    for c in considerations:
                        st.markdown(f"- {c}")

    # Metadata
    metadata = data.get("metadata", {})
    if metadata:
        st.divider()
        cols = st.columns(3)
        cols[0].metric("Decisions", metadata.get("decision_count", len(decisions)))
        cols[1].metric("Components", metadata.get("component_count", len(components)))
        cols[2].metric("Integrations", metadata.get("integration_count", len(integrations)))


# -----------------------------------------------------------------------------
# Main Content - Phase 3b: HOW (Architecture Decisions)
# -----------------------------------------------------------------------------

st.title("Architecture Decisions")

# Show the idea
idea_text = load_startup_idea()
if idea_text:
    st.markdown(
        f"""
<div style="background-color: #f0e6f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #6B2D8B; margin: 0.5rem 0 1.5rem 0;">
    <p style="font-size: 1rem; line-height: 1.5; margin: 0; color: #333;">{idea_text}</p>
</div>
""",
        unsafe_allow_html=True,
    )

# Check if any stages completed
any_completed = any(get_stage_status(s["id"]) for s in STAGES)

if not any_completed:
    st.info(
        "No Architecture Decisions completed yet. Run the Architecture Decisions workflow first."
    )
    st.stop()

# -----------------------------------------------------------------------------
# All Stages View
# -----------------------------------------------------------------------------

for stage in STAGES:
    stage_id = stage["id"]
    stage_name = stage["name"]
    stage_desc = stage["description"]
    renderer = stage.get("renderer", "markdown")

    if not get_stage_status(stage_id):
        continue

    with st.expander(f"**{stage_name}** - {stage_desc}", expanded=True):
        content = load_stage_output(stage_id, stage["output_file"])
        if content:
            if renderer == "architecture":
                render_architecture_decisions(content)
            else:
                st.markdown(content)
        else:
            st.warning(f"Output file not found: {stage['output_file']}")

# -----------------------------------------------------------------------------
# Feedback / Next Step Section
# -----------------------------------------------------------------------------


def is_workflow_locked() -> bool:
    """Check if the architecture-decisions workflow is locked."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    return lock_file.exists()


def handle_accept() -> None:
    """Handle accept and continue action."""
    from lib.workflow_runner import lock_workflow as _lock_wf

    _lock_wf(WORKFLOW_TYPE, SESSION_DIR)
    # Proceed to Phase 4: Story Generation
    st.session_state.run_story_workflow = True
    st.rerun()


st.divider()

if is_workflow_locked():
    # Build accomplishments
    accomplishments = ["Build vs buy analysis completed"]
    content = load_stage_output("architecture-decisions", "architecture_decisions.md")
    if content:
        data = extract_json_from_markdown(content)
        if data:
            dec_count = len(data.get("decisions", []))
            comp_count = len(data.get("components", []))
            if dec_count:
                accomplishments.append(f"{dec_count} architecture decisions documented")
            if comp_count:
                accomplishments.append(f"{comp_count} components defined")
        else:
            accomplishments.append("Architecture decisions documented")

    result = render_decision_gate(
        phase_name="Technical Design",
        accomplishments=accomplishments,
        next_phase_name="Story Generation",
        next_phase_preview="Turn capabilities and architecture into implementation-ready user stories.",
        next_phase_details=[
            "Generate stories with acceptance criteria for each capability",
            "Validate story traceability back to capabilities",
            "Order stories by dependency for implementation",
        ],
        on_continue="Continue to Story Generation",
        is_locked=True,
    )
    if result == "continue":
        st.session_state.run_story_workflow = True
        st.rerun()
else:
    # Workflow not locked - show chat-based feedback with intelligent agent
    stage_slugs = [s["id"] for s in STAGES]

    render_feedback_conversation(
        workflow_type=WORKFLOW_TYPE,
        workflow_display_name=WORKFLOW_DISPLAY_NAME,
        on_accept=handle_accept,
        stage_slugs=stage_slugs,
        system_goal=idea_text or "",
        session_dir=SESSION_DIR,
        next_stage_name="Story Generation",
    )
