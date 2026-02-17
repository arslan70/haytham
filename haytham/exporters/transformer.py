"""Transform raw stories JSON to ExportableStory format."""

import json
from pathlib import Path

from .models import ExportableStory, ExportOptions


def load_stories_from_json(
    stories_data: list[dict],
    options: ExportOptions | None = None,
) -> list[ExportableStory]:
    """
    Transform raw story dictionaries to ExportableStory objects.

    Args:
        stories_data: List of story dictionaries from generated_stories.json
        options: Export options for customization

    Returns:
        List of ExportableStory objects
    """
    options = options or ExportOptions()
    prefix = options.story_id_prefix

    # Build title → ID mapping for dependency resolution
    # Sort by order first to ensure consistent IDs
    sorted_stories = sorted(stories_data, key=lambda s: s.get("order", 0))
    title_to_id = {
        story["title"]: f"{prefix}-{i + 1:03d}" for i, story in enumerate(sorted_stories)
    }

    exportable = []
    for i, story in enumerate(sorted_stories):
        story_id = f"{prefix}-{i + 1:03d}"

        # Extract layer from labels
        layer = 4  # default to features
        for label in story.get("labels", []):
            if label.startswith("layer:"):
                try:
                    layer = int(label.split(":")[1])
                except (ValueError, IndexError):
                    pass
                break

        # Extract story type from labels
        story_type = "feature"
        for label in story.get("labels", []):
            if label.startswith("type:"):
                story_type = label.split(":")[1]
                break

        # Transform dependencies to IDs
        dependencies = story.get("dependencies", [])
        dependency_ids = [title_to_id[dep] for dep in dependencies if dep in title_to_id]

        exportable_story = ExportableStory(
            id=story_id,
            title=story.get("title", "Untitled"),
            description=story.get("description", ""),
            acceptance_criteria=story.get("acceptance_criteria", []),
            priority=story.get("priority", "medium"),
            order=story.get("order", i + 1),
            labels=story.get("labels", []),
            layer=layer,
            story_type=story_type,
            dependencies=dependencies,
            dependency_ids=dependency_ids,
            estimate=None,  # Future: AI-generated estimates
            epic=None,  # Future: Capability grouping
        )
        exportable.append(exportable_story)

    return exportable


def load_stories_from_file(
    session_path: Path,
    options: ExportOptions | None = None,
) -> list[ExportableStory]:
    """
    Load and transform stories from generated_stories.json file.

    Args:
        session_path: Path to session directory
        options: Export options for customization

    Returns:
        List of ExportableStory objects

    Raises:
        FileNotFoundError: If stories file doesn't exist
    """
    stories_file = session_path / "generated_stories.json"
    if not stories_file.exists():
        raise FileNotFoundError(f"Stories file not found: {stories_file}")

    with open(stories_file) as f:
        stories_data = json.load(f)

    return load_stories_from_json(stories_data, options)


def get_stories_by_layer(stories: list[ExportableStory]) -> dict[int, list[ExportableStory]]:
    """
    Group stories by layer.

    Args:
        stories: List of exportable stories

    Returns:
        Dictionary mapping layer number to list of stories
    """
    layers: dict[int, list[ExportableStory]] = {}
    for story in stories:
        if story.layer not in layers:
            layers[story.layer] = []
        layers[story.layer].append(story)
    return layers


def get_layer_summary(stories: list[ExportableStory]) -> dict[int, int]:
    """
    Get count of stories per layer.

    Args:
        stories: List of exportable stories

    Returns:
        Dictionary mapping layer number to story count
    """
    summary: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
    for story in stories:
        if story.layer in summary:
            summary[story.layer] += 1
    return summary
