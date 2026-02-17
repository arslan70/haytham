"""Build vs. Buy View - Recommendations for capabilities (Phase 3a: HOW).

This view displays build vs buy recommendations with:
1. Infrastructure Overview - high-level requirements
2. Recommended Stack - services with rationale
3. Alternatives - other options with pros/cons
"""

from lib.session_utils import METADATA_FILES, get_session_dir, load_environment, setup_paths

setup_paths()
load_environment()

import streamlit as st  # noqa: E402
import yaml  # noqa: E402
from components.feedback_conversation import (  # noqa: E402
    render_feedback_conversation,
)

# Workflow configuration
WORKFLOW_TYPE = "build-buy-analysis"
WORKFLOW_DISPLAY_NAME = "Build vs Buy Analysis"

SESSION_DIR = get_session_dir()


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


def load_build_buy_output() -> str | None:
    """Load build vs buy analysis output (any non-metadata .md file)."""
    stage_dir = SESSION_DIR / "build-buy-analysis"
    if not stage_dir.exists():
        return None
    for f in stage_dir.glob("*.md"):
        if f.name not in METADATA_FILES and f.stat().st_size > 100:
            return f.read_text()
    return None


def parse_build_buy_analysis(content: str) -> dict | None:
    """Parse the build vs buy analysis markdown/JSON output."""
    from haytham.agents.output_utils import extract_json_from_text

    return extract_json_from_text(content)


def render_infrastructure_overview(data: dict):
    """Render the infrastructure overview section."""
    st.markdown("## 🏗️ Infrastructure Overview")

    # System summary
    if "system_summary" in data:
        st.markdown(data["system_summary"])

    st.markdown("### What This System Needs")

    requirements = data.get("infrastructure_requirements", [])
    if requirements:
        cols = st.columns(min(len(requirements), 3))
        for i, req in enumerate(requirements):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{req.get('category', 'Infrastructure')}**")
                    st.caption(req.get("purpose", ""))
                    reqs = req.get("requirements", [])
                    if reqs:
                        for r in reqs:
                            st.markdown(f"• {r}")


def render_recommended_stack(data: dict):
    """Render the recommended stack section."""
    st.markdown("## 🎯 Recommended Stack")

    # Stack rationale
    if "stack_rationale" in data:
        st.info(data["stack_rationale"])

    stack = data.get("recommended_stack", [])

    # Group by recommendation type
    buy_items = [s for s in stack if s.get("recommendation") == "BUY"]
    build_items = [s for s in stack if s.get("recommendation") == "BUILD"]
    hybrid_items = [s for s in stack if s.get("recommendation") == "HYBRID"]

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🛒 BUY", len(buy_items))
    with col2:
        st.metric("🔧 BUILD", len(build_items))
    with col3:
        st.metric("🔀 HYBRID", len(hybrid_items))

    st.divider()

    # Render each recommendation
    for svc in stack:
        rec_type = svc.get("recommendation", "BUILD")
        emoji = "🛒" if rec_type == "BUY" else ("🔧" if rec_type == "BUILD" else "🔀")
        color = "green" if rec_type == "BUY" else ("violet" if rec_type == "BUILD" else "orange")

        with st.container(border=True):
            # Header
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {svc.get('name', 'Service')}")
                st.caption(svc.get("category", ""))
            with col2:
                st.markdown(f":{color}[**{emoji} {rec_type}**]")

            # Rationale - this is the key "why" explanation
            st.markdown(f"**Why:** {svc.get('rationale', '')}")

            # Details in columns
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Integration Effort:** {svc.get('integration_effort', 'TBD')}")
            with col2:
                st.markdown(f"**Pricing:** {svc.get('pricing_notes', 'See website')}")

            # Capabilities served
            caps = svc.get("capabilities_served", [])
            if caps:
                with st.expander("Capabilities Served"):
                    for cap in caps:
                        st.markdown(f"• {cap}")


def render_alternatives(data: dict):
    """Render the alternatives section."""
    st.markdown("## 🔄 Alternatives")
    st.caption("Other options to consider if the recommended stack doesn't fit your needs")

    alternatives = data.get("alternatives", [])

    if not alternatives:
        st.info("No alternatives provided for this analysis.")
        return

    for alt_section in alternatives:
        category = alt_section.get("category", "Category")
        recommended = alt_section.get("recommended", "")
        alts = alt_section.get("alternatives", [])

        with st.expander(f"**{category}** (Recommended: {recommended})", expanded=False):
            for alt in alts:
                with st.container(border=True):
                    st.markdown(f"**{alt.get('name', 'Alternative')}**")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Pros:**")
                        for pro in alt.get("pros", []):
                            st.markdown(f"✅ {pro}")
                    with col2:
                        st.markdown("**Cons:**")
                        for con in alt.get("cons", []):
                            st.markdown(f"⚠️ {con}")

                    best_for = alt.get("best_for", "")
                    if best_for:
                        st.caption(f"**Best for:** {best_for}")


def render_summary_footer(data: dict):
    """Render the summary footer with totals."""
    st.divider()
    st.markdown("## 📊 Summary")

    col1, col2 = st.columns(2)
    with col1:
        effort = data.get("total_integration_effort", "TBD")
        st.metric("Total Integration Effort", effort)
    with col2:
        cost = data.get("estimated_monthly_cost", "TBD")
        st.metric("Estimated Monthly Cost (MVP)", cost)


# -----------------------------------------------------------------------------
# Main Content - Phase 3a: HOW (Build vs Buy Analysis)
# -----------------------------------------------------------------------------

st.title("Build vs. Buy Analysis")

# Show the idea
idea_text = load_startup_idea()
if idea_text:
    st.info(idea_text)

# Load the analysis output
raw_output = load_build_buy_output()

if not raw_output:
    st.warning("No Build vs Buy analysis found. Run the Build vs Buy Analysis workflow first.")
    st.stop()

# Try to parse as structured JSON
analysis_data = parse_build_buy_analysis(raw_output)

if analysis_data:
    # Render structured sections
    render_infrastructure_overview(analysis_data)
    st.divider()
    render_recommended_stack(analysis_data)
    st.divider()
    render_alternatives(analysis_data)
    render_summary_footer(analysis_data)
else:
    # Fallback: render as markdown
    st.markdown("### Analysis Output")
    st.markdown(raw_output)


# -----------------------------------------------------------------------------
# Feedback / Next Step Section
# -----------------------------------------------------------------------------


def is_workflow_locked() -> bool:
    """Check if the build-buy-analysis workflow is locked."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    return lock_file.exists()


def handle_accept() -> None:
    """Handle accept and continue action."""
    from lib.workflow_runner import lock_workflow as _lock_wf

    _lock_wf(WORKFLOW_TYPE, SESSION_DIR)
    # Proceed to Phase 3b: Architecture Decisions (HOW)
    st.session_state.run_architecture_workflow = True
    st.rerun()


st.divider()

if is_workflow_locked():
    # Workflow is accepted/locked - show next step (Phase 3b: Architecture Decisions)
    st.success(f"{WORKFLOW_DISPLAY_NAME} has been accepted and locked.")
    st.markdown("#### Next Step: Architecture Decisions")
    st.markdown("Define key technical architecture decisions based on build vs buy analysis.")

    if st.button("Continue to Architecture Decisions", type="primary", use_container_width=True):
        st.session_state.run_architecture_workflow = True
        st.rerun()
else:
    # Workflow not locked - show chat-based feedback with intelligent agent
    stage_slugs = ["build-buy-analysis"]

    render_feedback_conversation(
        workflow_type=WORKFLOW_TYPE,
        workflow_display_name=WORKFLOW_DISPLAY_NAME,
        on_accept=handle_accept,
        stage_slugs=stage_slugs,
        system_goal=idea_text or "",
        session_dir=SESSION_DIR,
        next_stage_name="Architecture Decisions",
    )
