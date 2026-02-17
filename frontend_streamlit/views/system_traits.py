"""System Traits View - Display classified system traits (Phase 2b: WHAT).

This view displays the 5 system traits (interface, auth, deployment, data_layer, realtime)
classified by the system traits agent. Users review and accept before proceeding to
Phase 3: Technical Design (Build vs Buy Analysis).
"""

import re

from lib.session_utils import METADATA_FILES, get_session_dir, load_environment, setup_paths

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
WORKFLOW_TYPE = "system-traits"
WORKFLOW_DISPLAY_NAME = "System Traits"

# Badge colors for trait values
TRAIT_COLORS = {
    # interface
    "browser": "#1f77b4",
    "terminal": "#2ca02c",
    "mobile_native": "#d62728",
    "desktop_gui": "#9467bd",
    "api_only": "#ff7f0e",
    "none": "#999",
    # auth
    "multi_user": "#1f77b4",
    "single_user": "#2ca02c",
    # deployment
    "cloud_hosted": "#1f77b4",
    "app_store": "#d62728",
    "package_registry": "#ff7f0e",
    "local_install": "#2ca02c",
    "embedded": "#9467bd",
    # data_layer
    "remote_db": "#1f77b4",
    "local_storage": "#2ca02c",
    "file_system": "#ff7f0e",
    # realtime
    "true": "#d62728",
    "false": "#2ca02c",
}


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


def load_system_traits_output() -> str | None:
    """Load system traits output (any non-metadata .md file > 100 bytes)."""
    stage_dir = SESSION_DIR / "system-traits"
    if not stage_dir.exists():
        return None
    for f in stage_dir.glob("*.md"):
        if f.name not in METADATA_FILES and f.stat().st_size > 100:
            return f.read_text()
    return None


def parse_system_traits(content: str) -> list[dict]:
    """Parse the system traits markdown output into structured data.

    Expected format per trait:
    - **trait_name:** [value1, value2] or value
      Justification: One sentence...

    Returns list of dicts with keys: name, values, explanation
    """
    traits = []
    # Match trait lines: - **name:** value(s)\n  Explanation: ... (or legacy Justification:)
    pattern = re.compile(
        r"-\s+\*\*(\w+):\*\*\s+(.+?)\n\s+(?:Explanation|Justification):\s+(.+?)(?=\n\n|\n-\s+\*\*|\Z)",
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        name = match.group(1).strip()
        raw_values = match.group(2).strip()
        explanation = match.group(3).strip()

        # Parse values: [val1, val2] or single value
        if raw_values.startswith("[") and "]" in raw_values:
            bracket_content = raw_values[1 : raw_values.index("]")]
            values = [v.strip() for v in bracket_content.split(",") if v.strip()]
        else:
            values = [raw_values.split("(")[0].strip()]  # strip any (ambiguous) suffix

        traits.append(
            {
                "name": name,
                "values": values,
                "explanation": explanation,
            }
        )
    return traits


def render_trait_badge(value: str) -> str:
    """Render a color-coded badge for a trait value."""
    color = TRAIT_COLORS.get(value, "#666")
    display = value.replace("_", " ").title()
    return (
        f'<span style="display: inline-block; background: {color}18; color: {color}; '
        f"border: 1px solid {color}40; padding: 2px 10px; border-radius: 12px; "
        f'font-size: 13px; font-weight: 600; margin-right: 6px;">{display}</span>'
    )


TRAIT_DESCRIPTIONS = {
    "interface": "How users interact with the system",
    "auth": "Authentication model",
    "deployment": "Distribution method",
    "data_layer": "Primary data storage approach",
    "realtime": "Real-time data requirements",
}

TRAIT_ICONS = {
    "interface": "🖥️",
    "auth": "🔐",
    "deployment": "🚀",
    "data_layer": "💾",
    "realtime": "⚡",
}


# -----------------------------------------------------------------------------
# Main Content
# -----------------------------------------------------------------------------

st.title("System Traits Classification")

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

# Load the output
raw_output = load_system_traits_output()

if not raw_output:
    st.info(
        "System traits have not been classified yet. "
        "This stage runs automatically as part of the MVP Specification workflow."
    )
    st.stop()

# Parse and render traits
traits = parse_system_traits(raw_output)

if traits:
    for trait in traits:
        name = trait["name"]
        icon = TRAIT_ICONS.get(name, "📋")
        desc = TRAIT_DESCRIPTIONS.get(name, "")

        with st.container(border=True):
            # Header row
            col1, col2 = st.columns([2, 3])
            with col1:
                st.markdown(f"### {icon} {name.replace('_', ' ').title()}")
                if desc:
                    st.caption(desc)
            with col2:
                badges = "".join(render_trait_badge(v) for v in trait["values"])
                st.markdown(
                    f'<div style="padding-top: 12px;">{badges}</div>',
                    unsafe_allow_html=True,
                )

            # Justification
            st.markdown(f"*{trait['explanation']}*")
else:
    # Fallback: render raw markdown if parsing fails
    st.markdown("### Classification Output")
    st.markdown(raw_output)

# Summary metrics with explanations
if traits:
    st.divider()
    cols = st.columns(len(traits))
    for i, trait in enumerate(traits):
        with cols[i]:
            name = trait["name"].replace("_", " ").title()
            value_display = ", ".join(v.replace("_", " ") for v in trait["values"])
            st.metric(name, value_display)
            st.caption(trait["explanation"])

# -----------------------------------------------------------------------------
# Feedback / Next Step Section
# -----------------------------------------------------------------------------


def is_workflow_locked() -> bool:
    """Check if the system-traits workflow is locked."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    return lock_file.exists()


def handle_accept() -> None:
    """Handle accept and continue action."""
    from lib.workflow_runner import lock_workflow as _lock_wf

    _lock_wf(WORKFLOW_TYPE, SESSION_DIR)
    # Proceed to Phase 3a: Build vs Buy Analysis (HOW)
    st.session_state.run_build_buy_workflow = True
    st.rerun()


st.divider()

if is_workflow_locked():
    # Build accomplishments
    accomplishments = []
    if traits:
        accomplishments.append(f"{len(traits)} system traits classified")
        for trait in traits:
            values = ", ".join(v.replace("_", " ") for v in trait["values"])
            accomplishments.append(f"{trait['name']}: {values}")
    else:
        accomplishments.append("System traits classified")

    result = render_decision_gate(
        phase_name="System Traits",
        accomplishments=accomplishments,
        next_phase_name="Build vs Buy Analysis",
        next_phase_preview="For each capability, decide whether to build custom, buy a service, or use a hybrid approach.",
        next_phase_details=[
            "Evaluate existing services and tools for each capability",
            "Compare build effort vs integration cost",
            "Recommend build, buy, or hybrid per capability",
        ],
        on_continue="Continue to Build vs Buy Analysis",
        is_locked=True,
        verification_phase="WHAT",  # Gate 2 - WHAT phase verification
    )
    if result == "continue":
        st.session_state.run_build_buy_workflow = True
        st.rerun()
else:
    # Workflow not locked - show chat-based feedback with intelligent agent
    stage_slugs = ["system-traits"]

    render_feedback_conversation(
        workflow_type=WORKFLOW_TYPE,
        workflow_display_name=WORKFLOW_DISPLAY_NAME,
        on_accept=handle_accept,
        stage_slugs=stage_slugs,
        system_goal=idea_text or "",
        session_dir=SESSION_DIR,
        next_stage_name="Build vs Buy",
    )
