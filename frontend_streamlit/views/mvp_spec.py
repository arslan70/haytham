"""MVP Specification View - View MVP scope and capability model outputs with feedback."""

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
WORKFLOW_TYPE = "mvp-specification"
WORKFLOW_DISPLAY_NAME = "MVP Specification"


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
        "id": "mvp-scope",
        "name": "MVP Scope",
        "description": "Focused, achievable MVP definition",
        "output_file": "mvp_scope.md",
        "renderer": "markdown",
    },
    {
        "id": "capability-model",
        "name": "Capability Model",
        "description": "Business capabilities for implementation",
        "output_file": "capability_model.md",
        "renderer": "capability_model",
    },
]

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def strip_output_header(content: str) -> str:
    """Strip the '## Output' or '# Output' header from content."""
    # Remove "## Output" or "# Output" header at the start
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


def render_capability_model(content: str):
    """Render capability model JSON in a user-friendly format."""
    data = extract_json_from_markdown(content)
    if not data:
        st.warning(
            "Could not parse capability model as structured data. "
            "This usually means the agent hit a token limit. "
            "Try re-running the MVP Specification workflow."
        )
        st.markdown(content)
        return

    # Summary Section
    summary = data.get("summary", {})
    if summary:
        st.markdown(
            f"""
<div style="background-color: #f0e6f6; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #6B2D8B; margin-bottom: 1.5rem;">
    <h3 style="margin: 0 0 0.5rem 0; color: #6B2D8B;">{summary.get("system_name", "System")}</h3>
    <p style="margin: 0 0 1rem 0; color: #333; font-size: 1.05rem;">{summary.get("system_purpose", "")}</p>
    <p style="margin: 0; color: #666;"><strong>Target Users:</strong> {summary.get("primary_user_segment", "N/A")}</p>
</div>
""",
            unsafe_allow_html=True,
        )

    capabilities = data.get("capabilities", {})

    # Functional Capabilities
    functional = capabilities.get("functional", [])
    if functional:
        st.markdown("### Functional Capabilities")
        st.caption(f"{len(functional)} capabilities defined")

        for cap in functional:
            with st.expander(f"**{cap.get('name', 'Capability')}**", expanded=False):
                st.markdown(f"**Description:** {cap.get('description', '')}")
                st.markdown(f"**User Flow:** {cap.get('user_flow', 'N/A')}")

                criteria = cap.get("acceptance_criteria", [])
                if criteria:
                    st.markdown("**Acceptance Criteria:**")
                    for c in criteria:
                        st.markdown(f"- {c}")

                rationale = cap.get("rationale", "")
                if rationale:
                    st.info(f"**Rationale:** {rationale}")

    # Non-Functional Capabilities
    non_functional = capabilities.get("non_functional", [])
    if non_functional:
        st.markdown("### Non-Functional Requirements")
        st.caption(f"{len(non_functional)} requirements defined")

        # Group by category
        categories = {}
        for nf in non_functional:
            cat = nf.get("category", "other").title()
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(nf)

        for category, items in categories.items():
            st.markdown(f"#### {category}")
            for nf in items:
                with st.expander(f"**{nf.get('name', 'Requirement')}**", expanded=False):
                    st.markdown(f"**Description:** {nf.get('description', '')}")
                    st.markdown(f"**Requirement:** {nf.get('requirement', '')}")
                    st.markdown(f"**Measurement:** {nf.get('measurement', '')}")
                    rationale = nf.get("rationale", "")
                    if rationale:
                        st.info(f"**Rationale:** {rationale}")

    # Metadata
    metadata = data.get("metadata", {})
    if metadata:
        st.divider()
        cols = st.columns(3)
        cols[0].metric("Functional", metadata.get("functional_count", 0))
        cols[1].metric("Non-Functional", metadata.get("non_functional_count", 0))
        flows = metadata.get("flows_covered", [])
        cols[2].metric("User Flows", len(flows))

        if flows:
            st.caption(f"**Flows:** {', '.join(flows)}")


# -----------------------------------------------------------------------------
# Main Content
# -----------------------------------------------------------------------------

st.title("MVP Specification Results")

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
    st.info("No MVP Specification stages completed yet.")
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
            if renderer == "capability_model":
                render_capability_model(content)
            else:
                st.markdown(content)
        else:
            st.warning(f"Output file not found: {stage['output_file']}")

# -----------------------------------------------------------------------------
# Feedback / Next Step Section
# -----------------------------------------------------------------------------


def is_workflow_locked() -> bool:
    """Check if the mvp-specification workflow is locked."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    return lock_file.exists()


def handle_accept() -> None:
    """Handle accept and continue action."""
    from lib.workflow_runner import lock_workflow as _lock_wf

    _lock_wf(WORKFLOW_TYPE, SESSION_DIR)
    # Navigate to System Traits review (output already exists from MVP workflow)
    st.session_state.navigate_to = "system_traits"
    st.rerun()


st.divider()

if is_workflow_locked():
    # Build accomplishments from session artifacts
    accomplishments = ["MVP scope defined"]
    cap_content = load_stage_output("capability-model", "capability_model.md")
    if cap_content:
        cap_data = extract_json_from_markdown(cap_content)
        if cap_data:
            func_count = len(cap_data.get("capabilities", {}).get("functional", []))
            nf_count = len(cap_data.get("capabilities", {}).get("non_functional", []))
            if func_count:
                accomplishments.append(f"{func_count} functional capabilities extracted")
            if nf_count:
                accomplishments.append(f"{nf_count} non-functional requirements defined")
        else:
            accomplishments.append("Capability model generated")

    result = render_decision_gate(
        phase_name="MVP Specification",
        accomplishments=accomplishments,
        next_phase_name="System Traits",
        next_phase_preview="Classify the type of system you're building to guide technical decisions.",
        next_phase_details=[
            "Determine interface type (web, mobile, CLI, API)",
            "Identify authentication and deployment models",
            "Classify data storage and real-time requirements",
        ],
        on_continue="Review System Traits",
        is_locked=True,
    )
    if result == "continue":
        st.session_state.navigate_to = "system_traits"
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
        next_stage_name="System Traits",
    )
