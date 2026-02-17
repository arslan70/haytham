"""
Haytham - Startup Idea Validation Tool

Main entry point with dynamic navigation based on project state.
Run with: streamlit run frontend_streamlit/Haytham.py
"""

from lib.session_utils import METADATA_FILES, get_session_dir, setup_paths

setup_paths()

import streamlit as st  # noqa: E402
import yaml  # noqa: E402

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Haytham",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS globally (must be after page_config)
from frontend_streamlit.components.styling import load_css

load_css()

# Sidebar branding — renders "∞ Haytham" in the top-left corner
_HAYTHAM_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 40">
  <text x="0" y="30" font-family="Inter, -apple-system, BlinkMacSystemFont, sans-serif"
        font-size="28" font-weight="800" fill="#6B2D8B">
    <tspan fill="#8B5FAF">&#x221E;</tspan> Haytham
  </text>
</svg>"""
st.logo(_HAYTHAM_LOGO_SVG, size="medium")

SESSION_DIR = get_session_dir()


def has_project() -> bool:
    """Check if a project exists."""
    project_file = SESSION_DIR / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return bool(data.get("system_goal"))
        except Exception:
            pass
    return False


def is_workflow_locked(workflow_type: str) -> bool:
    """Check if a workflow has been accepted/locked."""
    lock_file = SESSION_DIR / f".{workflow_type}.locked"
    return lock_file.exists()


def _has_stage_output(stage_slug: str) -> bool:
    """Check if a stage directory contains any real output .md file > 100 bytes.

    Ignores metadata files (checkpoint.md, user_feedback.md).
    This avoids hardcoding agent output filenames which can differ
    from the stage slug (e.g. build_buy_advisor.md vs build_buy_analysis.md).
    """
    stage_dir = SESSION_DIR / stage_slug
    if not stage_dir.exists():
        return False
    for f in stage_dir.glob("*.md"):
        if f.name not in METADATA_FILES and f.stat().st_size > 100:
            return True
    return False


def has_idea_validation() -> bool:
    """Check if idea validation has run."""
    return _has_stage_output("validation-summary") or _has_stage_output("risk-assessment")


def has_mvp_specification() -> bool:
    """Check if MVP specification has run."""
    return _has_stage_output("capability-model")


def has_stories() -> bool:
    """Check if stories have been generated."""
    return _has_stage_output("story-generation")


def has_system_traits() -> bool:
    """Check if system traits have been classified."""
    return _has_stage_output("system-traits")


def has_build_buy_analysis() -> bool:
    """Check if build vs buy analysis has run."""
    return _has_stage_output("build-buy-analysis")


def has_architecture_decisions() -> bool:
    """Check if architecture decisions has run."""
    return _has_stage_output("architecture-decisions")


def has_technical_design() -> bool:
    """Check if technical design has run (outputs exist)."""
    return has_build_buy_analysis() or has_architecture_decisions()


# -----------------------------------------------------------------------------
# Dynamic Navigation - Four-Phase Workflow (ADR-016)
#
# Phase 1: WHY (Idea Validation) - Is this idea worth pursuing?
# Phase 2: WHAT (MVP Specification) - What should we build first?
# Phase 3: HOW (Technical Design) - How should we build it?
# Phase 4: STORIES (Implementation Planning) - What are the tasks?
# -----------------------------------------------------------------------------

# Check if there's a pending workflow to run
workflow_pending = (
    st.session_state.get("new_idea") is not None
    or st.session_state.get("unrelated_redirect") is not None
    or st.session_state.get("run_mvp_workflow") is not None
    or st.session_state.get("run_build_buy_workflow") is not None
    or st.session_state.get("run_architecture_workflow") is not None
    or st.session_state.get("run_story_workflow") is not None
)

if has_project() or workflow_pending:
    # Check for navigation request
    navigate_to = st.session_state.pop("navigate_to", None)

    # Project exists - build navigation based on workflow progress
    pages: dict[str, list] = {"": []}  # "" key = ungrouped (Project)
    # Track navigate_to target page for explicit redirect after nav is built
    _navigate_target = None

    pages[""].append(
        st.Page(
            "views/dashboard.py",
            title="Project",
            icon="🏠",
            default=not workflow_pending and navigate_to is None,
        )
    )

    # -------------------------------------------------------------------------
    # Phase 1: WHY (Idea Validation)
    # -------------------------------------------------------------------------
    why_status = (
        "✅" if is_workflow_locked("idea-validation") else ("🔵" if has_idea_validation() else "⚪")
    )
    why_label = f"{why_status} Phase 1: WHY"

    if has_idea_validation():
        _discovery_page = st.Page(
            "views/discovery.py",
            title="Idea Analysis",
            icon="📄",
            default=navigate_to == "discovery",
        )
        if navigate_to == "discovery":
            _navigate_target = _discovery_page
        pages[why_label] = [_discovery_page]
    else:
        pages[why_label] = []

    # -------------------------------------------------------------------------
    # Phase 2: WHAT (MVP Specification)
    # -------------------------------------------------------------------------
    what_status = (
        "✅" if is_workflow_locked("system-traits") else ("🔵" if has_mvp_specification() else "⚪")
    )
    what_label = f"{what_status} Phase 2: WHAT"

    if is_workflow_locked("idea-validation") and has_mvp_specification():
        _mvp_page = st.Page(
            "views/mvp_spec.py",
            title="MVP Specification",
            icon="📑",
            default=navigate_to == "mvp_spec",
        )
        if navigate_to == "mvp_spec":
            _navigate_target = _mvp_page
        what_pages = [_mvp_page]
        if is_workflow_locked("mvp-specification"):
            _traits_page = st.Page(
                "views/system_traits.py",
                title="System Traits",
                icon="🧬",
                default=navigate_to == "system_traits",
            )
            if navigate_to == "system_traits":
                _navigate_target = _traits_page
            what_pages.append(_traits_page)
        pages[what_label] = what_pages
    else:
        pages[what_label] = []

    # -------------------------------------------------------------------------
    # Phase 3: HOW (Technical Design)
    # -------------------------------------------------------------------------
    how_locked = is_workflow_locked("architecture-decisions") or is_workflow_locked(
        "technical-design"
    )
    how_in_progress = has_build_buy_analysis() or has_architecture_decisions()
    how_status = "✅" if how_locked else ("🔵" if how_in_progress else "⚪")
    how_label = f"{how_status} Phase 3: HOW"
    how_pages = []

    if is_workflow_locked("system-traits") and has_build_buy_analysis():
        _bb_page = st.Page(
            "views/build_buy.py",
            title="Build vs Buy",
            icon="🛒",
            default=navigate_to == "build_buy",
        )
        if navigate_to == "build_buy":
            _navigate_target = _bb_page
        how_pages.append(_bb_page)

    if is_workflow_locked("build-buy-analysis") and has_architecture_decisions():
        _arch_page = st.Page(
            "views/architecture.py",
            title="Architecture",
            icon="🏗️",
            default=navigate_to == "architecture",
        )
        if navigate_to == "architecture":
            _navigate_target = _arch_page
        how_pages.append(_arch_page)

    pages[how_label] = how_pages

    # -------------------------------------------------------------------------
    # Phase 4: STORIES (Implementation Planning)
    # -------------------------------------------------------------------------
    stories_locked = is_workflow_locked("story-generation")
    stories_status = "✅" if stories_locked else ("🔵" if has_stories() else "⚪")
    stories_label = f"{stories_status} Phase 4: STORIES"

    if (
        is_workflow_locked("architecture-decisions") or is_workflow_locked("technical-design")
    ) and has_stories():
        _stories_page = st.Page(
            "views/stories.py", title="Stories", icon="📋", default=navigate_to == "stories"
        )
        if navigate_to == "stories":
            _navigate_target = _stories_page
        pages[stories_label] = [_stories_page]
    else:
        pages[stories_label] = []

    # Only show Execution when there's a workflow to run
    _execution_page = None
    if workflow_pending:
        _execution_page = st.Page("views/execution.py", title="Execution", icon="🔧", default=True)
        pages[""].append(_execution_page)

    # Build flat page list for st.navigation - only include non-empty sections
    nav_pages: dict[str, list] = {}
    for section, section_pages in pages.items():
        if section_pages:
            if section == "":
                # Ungrouped pages go under a blank section
                nav_pages.setdefault("", []).extend(section_pages)
            else:
                nav_pages[section] = section_pages

    # If only ungrouped pages, pass as flat list
    if list(nav_pages.keys()) == [""]:
        nav = st.navigation(nav_pages[""])
    else:
        nav = st.navigation(nav_pages)

    # Force redirect to execution page when a workflow is pending.
    # st.navigation() remembers the user's last page, so default=True alone
    # won't switch away from e.g. discovery.py. We must explicitly switch.
    if _execution_page is not None and nav.title != "Execution":
        st.switch_page(_execution_page)

    # Force redirect to navigate_to target page after workflow completion.
    # When the Execution page disappears (workflow done), st.navigation falls
    # back to the remembered page which no longer exists, landing on dashboard.
    # Explicit switch_page ensures we reach the intended results page.
    if _navigate_target is not None and nav.title != _navigate_target.title:
        st.switch_page(_navigate_target)

else:
    # No project - only show new project page
    pages_list = [
        st.Page("views/new_project.py", title="New Project", icon="🚀", default=True),
    ]
    nav = st.navigation(pages_list)

nav.run()
