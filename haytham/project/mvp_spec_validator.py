"""MVP Specification Validator for the Story-to-Implementation Pipeline.

Validates parsed MVP specifications to catch errors before
they propagate to downstream pipeline stages.

Reference: ADR-001a: Validation Rules
"""

from collections import defaultdict

from .mvp_spec_parser import ParsedMVPSpec


def validate_mvp_spec(parsed_spec: ParsedMVPSpec) -> list[str]:
    """Validate parsed MVP spec.

    Returns list of errors (empty if valid).

    Checks:
    - Entity completeness: Every entity referenced in stories exists in domain model
    - Story ID uniqueness: No duplicate S-XXX
    - Entity ID uniqueness: No duplicate E-XXX
    - Dependency validity: All dependencies reference existing IDs
    - No circular dependencies (between stories)
    - Required fields present
    """
    errors = []

    # Collect all IDs
    entity_ids = {e.id for e in parsed_spec.entities}
    story_ids = {s.id for s in parsed_spec.stories}
    all_ids = entity_ids | story_ids

    # Check entity completeness
    errors.extend(_check_entity_completeness(parsed_spec, entity_ids))

    # Check ID uniqueness
    errors.extend(_check_id_uniqueness(parsed_spec))

    # Check dependency validity
    errors.extend(_check_dependency_validity(parsed_spec, all_ids))

    # Check for circular dependencies
    errors.extend(_check_circular_dependencies(parsed_spec))

    # Check required fields
    errors.extend(_check_required_fields(parsed_spec))

    return errors


def _check_entity_completeness(parsed_spec: ParsedMVPSpec, entity_ids: set[str]) -> list[str]:
    """Check that all entities referenced in stories exist."""
    errors = []

    for story in parsed_spec.stories:
        for dep in story.depends_on:
            if dep.startswith("E-") and dep not in entity_ids:
                errors.append(
                    f"Story {story.id} depends on entity {dep} which does not exist in domain model"
                )

    # Also check entity relationships
    for entity in parsed_spec.entities:
        for rel in entity.relationships:
            if rel.target not in entity_ids:
                errors.append(
                    f"Entity {entity.id} has relationship to {rel.target} which does not exist"
                )

    return errors


def _check_id_uniqueness(parsed_spec: ParsedMVPSpec) -> list[str]:
    """Check for duplicate IDs."""
    errors = []

    # Check entity IDs
    entity_id_counts: dict[str, int] = defaultdict(int)
    for entity in parsed_spec.entities:
        entity_id_counts[entity.id] += 1

    for entity_id, count in entity_id_counts.items():
        if count > 1:
            errors.append(f"Duplicate entity ID: {entity_id} appears {count} times")

    # Check story IDs
    story_id_counts: dict[str, int] = defaultdict(int)
    for story in parsed_spec.stories:
        story_id_counts[story.id] += 1

    for story_id, count in story_id_counts.items():
        if count > 1:
            errors.append(f"Duplicate story ID: {story_id} appears {count} times")

    return errors


def _check_dependency_validity(parsed_spec: ParsedMVPSpec, all_ids: set[str]) -> list[str]:
    """Check that all dependencies reference existing IDs."""
    errors = []

    for story in parsed_spec.stories:
        for dep in story.depends_on:
            if dep not in all_ids:
                errors.append(f"Story {story.id} depends on {dep} which does not exist")

    return errors


def _check_circular_dependencies(parsed_spec: ParsedMVPSpec) -> list[str]:
    """Check for circular dependencies between stories.

    Uses depth-first search to detect cycles.
    """
    errors = []

    # Build adjacency list (story -> stories it depends on)
    story_deps: dict[str, list[str]] = {}
    for story in parsed_spec.stories:
        # Only include story dependencies (S-XXX), not entity dependencies
        story_deps[story.id] = [dep for dep in story.depends_on if dep.startswith("S-")]

    # DFS to detect cycles
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(story_id: str, path: list[str]) -> list[str] | None:
        """Return cycle path if cycle detected, None otherwise."""
        if story_id in rec_stack:
            # Found cycle - return the cycle path
            cycle_start = path.index(story_id)
            return path[cycle_start:] + [story_id]

        if story_id in visited:
            return None

        visited.add(story_id)
        rec_stack.add(story_id)
        path.append(story_id)

        for dep in story_deps.get(story_id, []):
            if dep in story_deps:  # Only check if dep is a story we know about
                cycle = has_cycle(dep, path.copy())
                if cycle:
                    return cycle

        rec_stack.remove(story_id)
        return None

    for story_id in story_deps:
        if story_id not in visited:
            cycle = has_cycle(story_id, [])
            if cycle:
                cycle_str = " -> ".join(cycle)
                errors.append(f"Circular dependency detected: {cycle_str}")
                break  # Only report first cycle found

    return errors


def _check_required_fields(parsed_spec: ParsedMVPSpec) -> list[str]:
    """Check that required fields are present."""
    errors = []

    # Entities must have name and at least one attribute
    for entity in parsed_spec.entities:
        if not entity.name:
            errors.append(f"Entity {entity.id} is missing name")
        if not entity.attributes:
            errors.append(f"Entity {entity.id} has no attributes defined")

    # Stories must have title and user_story
    for story in parsed_spec.stories:
        if not story.title:
            errors.append(f"Story {story.id} is missing title")
        if not story.user_story:
            errors.append(f"Story {story.id} is missing user story")

    return errors


def validate_mvp_spec_text(text: str) -> list[str]:
    """Validate MVP spec text for structural requirements.

    This validates the raw text before parsing, checking for
    required sections and markers.
    """
    from .mvp_spec_parser import MVPSpecParser

    parser = MVPSpecParser()
    return parser.validate_completeness(text)
