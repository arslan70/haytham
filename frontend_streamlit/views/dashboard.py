"""Dashboard View - Main project overview with Genesis progress tracking."""

import json

from lib.session_utils import get_session_dir, setup_paths

setup_paths()

import streamlit as st  # noqa: E402
import yaml  # noqa: E402
from components.progress_bar import render_genesis_progress  # noqa: E402

SESSION_DIR = get_session_dir()

METADATA_FILES = {"checkpoint.md", "user_feedback.md"}


def load_startup_idea():
    """Load startup idea from project.yaml."""
    project_file = SESSION_DIR / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return data.get("system_goal", "")
        except Exception:
            pass
    return None


def load_artifact_counts():
    """Load artifact counts from VectorDB."""
    try:
        from haytham.state.vector_db import SystemStateDB

        db_path = SESSION_DIR / "vector_db"
        if db_path.exists():
            db = SystemStateDB(str(db_path))
            return {
                "capabilities": len(db.get_capabilities()),
                "decisions": len(db.get_decisions()),
                "entities": len(db.get_entities()),
            }
    except Exception:
        pass
    return {"capabilities": 0, "decisions": 0, "entities": 0}


def load_stories_count():
    """Load stories count from story-generation output or generated_stories.json."""
    import re

    # First check markdown output
    story_md = SESSION_DIR / "story-generation" / "story_generation.md"
    if story_md.exists():
        try:
            content = story_md.read_text()
            # Count STORY-XXX patterns
            story_count = len(re.findall(r"###\s*STORY-\d+:", content))
            if story_count > 0:
                return story_count
        except Exception:
            pass

    # Fallback to JSON
    stories_file = SESSION_DIR / "generated_stories.json"
    if stories_file.exists():
        try:
            stories = json.loads(stories_file.read_text())
            return len(stories) if isinstance(stories, list) else 0
        except Exception:
            pass
    return 0


def _is_locked(workflow_type: str) -> bool:
    return (SESSION_DIR / f".{workflow_type}.locked").exists()


def _has_stage_output(stage_slug: str) -> bool:
    stage_dir = SESSION_DIR / stage_slug
    if not stage_dir.exists():
        return False
    for f in stage_dir.glob("*.md"):
        if f.name not in METADATA_FILES and f.stat().st_size > 100:
            return True
    return False


# Load data
idea_text = load_startup_idea()
counts = load_artifact_counts()
stories = load_stories_count()

# Determine completion based on actual OUTPUT FILES
idea_validation_complete = (SESSION_DIR / "validation-summary" / "validation_scorer.md").exists()
mvp_specification_complete = (
    SESSION_DIR / "capability-model" / "capability_model.md"
).exists() and counts["capabilities"] > 0
build_buy_complete = _has_stage_output("build-buy-analysis")
architecture_complete = _has_stage_output("architecture-decisions")
story_generation_complete = stories > 0

# =============================================================================
# Dashboard UI
# =============================================================================

st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
st.header("Your Project")

# Show the idea prominently
st.markdown(
    f"""
<div style="background-color: #f0e6f6; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #6B2D8B; margin: 1rem 0;">
    <p style="font-size: 1.1rem; line-height: 1.6; margin: 0; color: #333;">{idea_text}</p>
</div>
""",
    unsafe_allow_html=True,
)

# Genesis progress bar
render_genesis_progress()

st.divider()

# Phase summary table
st.markdown("##### Phase Overview")

phase_rows = [
    {
        "phase": "1. WHY",
        "name": "Idea Validation",
        "locked": _is_locked("idea-validation"),
        "has_output": idea_validation_complete,
        "key_output": "GO/NO-GO recommendation",
        "nav": "discovery",
        "run_key": "new_idea",
        "run_value": idea_text,
    },
    {
        "phase": "2. WHAT",
        "name": "MVP Specification",
        "locked": _is_locked("mvp-specification"),
        "has_output": mvp_specification_complete,
        "key_output": f"{counts['capabilities']} capabilities"
        if counts["capabilities"] > 0
        else "Capabilities & scope",
        "nav": "mvp_spec",
        "run_key": "run_mvp_workflow",
        "run_value": True,
        "requires_lock": "idea-validation",
    },
    {
        "phase": "3. HOW",
        "name": "Technical Design",
        "locked": _is_locked("architecture-decisions"),
        "has_output": build_buy_complete or architecture_complete,
        "key_output": f"{counts['decisions']} decisions"
        if counts["decisions"] > 0
        else "Build/buy & architecture",
        "nav": "build_buy",
        "run_key": "run_build_buy_workflow",
        "run_value": True,
        "requires_lock": "system-traits",
    },
    {
        "phase": "4. STORIES",
        "name": "Implementation",
        "locked": _is_locked("story-generation"),
        "has_output": story_generation_complete,
        "key_output": f"{stories} stories" if stories > 0 else "Implementation stories",
        "nav": "stories",
        "run_key": "run_story_workflow",
        "run_value": True,
        "requires_lock": "architecture-decisions",
    },
]

for row in phase_rows:
    if row["locked"]:
        status = "✅ Complete"
        status_color = "#4CAF50"
    elif row["has_output"]:
        status = "🔵 In Review"
        status_color = "#2196F3"
    else:
        status = "⚪ Pending"
        status_color = "#999"

    cols = st.columns([1, 2, 2, 2])
    with cols[0]:
        st.markdown(f"**{row['phase']}**")
    with cols[1]:
        st.markdown(row["name"])
    with cols[2]:
        st.markdown(
            f"<span style='color: {status_color}; font-size: 13px;'>{status}</span>",
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.caption(row["key_output"])

st.divider()

# Determine next action and show prominent CTA
next_action = None
for row in phase_rows:
    if row["locked"]:
        continue
    if row["has_output"]:
        # Phase has output but not locked - user should review
        next_action = ("review", row)
        break
    # Phase has no output - needs to run
    requires = row.get("requires_lock")
    if requires and not _is_locked(requires):
        # Can't run yet - dependency not met
        continue
    next_action = ("run", row)
    break

if next_action:
    action_type, row = next_action
    if action_type == "review":
        st.info(f"**Next:** Review and accept {row['name']} results")
        if st.button(f"Review {row['name']}", type="primary", use_container_width=True):
            st.session_state.navigate_to = row["nav"]
            st.rerun()
    else:
        st.warning(f"**Next:** Run {row['name']}")
        if st.button(f"Run {row['name']}", type="primary", use_container_width=True):
            st.session_state[row["run_key"]] = row["run_value"]
            st.rerun()
elif all(r["locked"] for r in phase_rows):
    st.success("All Genesis phases complete! Your stories are ready for implementation.")
    if st.button("View Stories", type="primary", use_container_width=True):
        st.session_state.navigate_to = "stories"
        st.rerun()
