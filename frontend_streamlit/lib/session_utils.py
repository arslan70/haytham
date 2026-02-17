"""Session utilities for Streamlit.

Helper functions for session management, project files, and status checking.
"""

import json
import shutil
import sys
from pathlib import Path

import yaml

# Default session directory (relative to project root)
SESSION_DIR = Path(__file__).parent.parent.parent / "session"

# Files that are metadata (checkpoints, feedback), not stage output
METADATA_FILES = {"checkpoint.md", "user_feedback.md"}


def get_session_dir() -> Path:
    """Get the session directory path."""
    return SESSION_DIR


def setup_paths() -> None:
    """Add project root and frontend_streamlit to sys.path."""
    project_root = str(Path(__file__).parent.parent.parent)
    streamlit_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if streamlit_root not in sys.path:
        sys.path.insert(0, streamlit_root)


def load_environment() -> None:
    """Load .env from project root."""
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)


def clear_session() -> None:
    """Clear all session data for a fresh start."""
    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def create_project_file(system_goal: str) -> None:
    """Create project.yaml with the startup idea.

    Args:
        system_goal: The startup idea/goal
    """
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    project_file = SESSION_DIR / "project.yaml"
    data = {"system_goal": system_goal}
    project_file.write_text(yaml.safe_dump(data))


def get_system_goal() -> str | None:
    """Get the startup idea from project.yaml.

    Returns:
        The system goal string, or None if not set
    """
    project_file = SESSION_DIR / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return data.get("system_goal")
        except Exception:
            pass
    return None


def get_validation_recommendation() -> str | None:
    """Get the validation recommendation (GO/NO-GO/PIVOT).

    Parses the validation summary markdown to extract the recommendation.

    Returns:
        "GO", "NO-GO", "PIVOT", or None if not found
    """
    summary_dir = SESSION_DIR / "validation-summary"
    if not summary_dir.exists():
        return None

    # Look for markdown files in validation-summary
    for f in summary_dir.glob("*.md"):
        try:
            content = f.read_text().upper()
            # Check for recommendations (order matters - check NO-GO first)
            if "NO-GO" in content or "NO GO" in content:
                return "NO-GO"
            elif "PIVOT" in content:
                return "PIVOT"
            elif "GO" in content:
                return "GO"
        except Exception:
            continue

    return None


def get_workflow_status() -> dict[str, bool]:
    """Get the completion status of all workflows.

    Returns:
        Dict with workflow completion flags
    """
    return {
        "idea_validation_complete": (SESSION_DIR / "validation-summary").exists(),
        "mvp_specification_complete": (SESSION_DIR / "capability-model").exists(),
        "story_generation_complete": (SESSION_DIR / "generated_stories.json").exists()
        and _has_stories(),
        "has_project": (SESSION_DIR / "project.yaml").exists(),
    }


def _has_stories() -> bool:
    """Check if generated stories exist and have content."""
    stories_file = SESSION_DIR / "generated_stories.json"
    if stories_file.exists():
        try:
            stories = json.loads(stories_file.read_text())
            return isinstance(stories, list) and len(stories) > 0
        except Exception:
            pass
    return False


def get_artifact_counts() -> dict[str, int]:
    """Get counts of artifacts from VectorDB.

    Returns:
        Dict with capability, decision, and entity counts
    """
    try:
        # Lazy import to avoid circular deps
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


def get_stories_count() -> int:
    """Get count of generated stories.

    Returns:
        Number of stories, or 0 if none
    """
    stories_file = SESSION_DIR / "generated_stories.json"
    if stories_file.exists():
        try:
            stories = json.loads(stories_file.read_text())
            return len(stories) if isinstance(stories, list) else 0
        except Exception:
            pass
    return 0


def has_discovery_outputs() -> bool:
    """Check if Idea Validation outputs exist."""
    return (SESSION_DIR / "idea-analysis").exists()


def has_mvp_spec() -> bool:
    """Check if MVP specification exists."""
    return (SESSION_DIR / "mvp-specification" / "mvp_spec.md").exists()
