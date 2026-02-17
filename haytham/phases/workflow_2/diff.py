"""Workflow 2: Architecture Diff Computation.

This module implements the diff-based architecture awareness as defined in ADR-005.
The core principle is that instead of determining modes (greenfield/incremental/revision),
we compute a diff that tells agents exactly what needs attention.

The diff becomes the single source of truth for what the architect agents should do.
"""

from dataclasses import dataclass, field


@dataclass
class ArchitectureDiff:
    """Computed diff - what needs attention in architecture.

    This dataclass captures the delta between the current VectorDB state
    and what needs to be addressed. Agents process this diff rather than
    determining their own mode of operation.

    The "mode" becomes emergent from the diff:
    - All capabilities uncovered → behaves like "greenfield"
    - Some uncovered, none affected → behaves like "incremental"
    - Has affected decisions → behaves like "revision"
    - Empty diff → nothing to do

    Attributes:
        uncovered_capabilities: Capability IDs (CAP-*) with no active decisions serving them.
            These are new or orphaned capabilities that need architecture decisions.

        capabilities_without_stories: Capability IDs (CAP-*) that have decisions but no stories.
            These need stories generated (story_generation stage).

        affected_decisions: Decision IDs (DEC-*) that serve superseded capabilities.
            These decisions may need to be revised or superseded themselves.

        affected_entities: Entity IDs (ENT-*) referenced by affected decisions.
            These entities may need updates when decisions change.

        affected_stories: Story IDs from Backlog.md that implement superseded capabilities.
            These stories need review and may need to be updated or archived.
    """

    uncovered_capabilities: list[str] = field(default_factory=list)
    capabilities_without_stories: list[str] = field(default_factory=list)
    affected_decisions: list[str] = field(default_factory=list)
    affected_entities: list[str] = field(default_factory=list)
    affected_stories: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if there's nothing to do."""
        return (
            not self.uncovered_capabilities
            and not self.capabilities_without_stories
            and not self.affected_decisions
            and not self.affected_entities
            and not self.affected_stories
        )

    def needs_stories(self) -> bool:
        """Check if stories need to be generated."""
        return bool(self.uncovered_capabilities or self.capabilities_without_stories)

    def is_greenfield(self) -> bool:
        """Check if this is effectively a greenfield scenario.

        Greenfield means all capabilities are uncovered (no existing decisions).
        """
        return bool(self.uncovered_capabilities) and not self.affected_decisions

    def has_revisions_needed(self) -> bool:
        """Check if existing architecture needs revision."""
        return bool(self.affected_decisions or self.affected_entities or self.affected_stories)

    def summary(self) -> str:
        """Get a human-readable summary of the diff."""
        if self.is_empty():
            return "No architecture changes needed"

        parts = []
        if self.uncovered_capabilities:
            parts.append(f"{len(self.uncovered_capabilities)} uncovered capabilities")
        if self.capabilities_without_stories:
            parts.append(f"{len(self.capabilities_without_stories)} capabilities need stories")
        if self.affected_decisions:
            parts.append(f"{len(self.affected_decisions)} affected decisions")
        if self.affected_entities:
            parts.append(f"{len(self.affected_entities)} affected entities")
        if self.affected_stories:
            parts.append(f"{len(self.affected_stories)} affected stories")

        return ", ".join(parts)


def compute_architecture_diff(
    capabilities: list[dict],
    decisions: list[dict],
    entities: list[dict],
    stories: list[dict],
) -> ArchitectureDiff:
    """Compute what needs attention - pure function, easily testable.

    This is the core algorithm from ADR-005 that determines what the
    architect agents need to address.

    Args:
        capabilities: All capabilities from VectorDB (via get_capabilities()).
            Each dict should have at minimum: id, superseded_by.

        decisions: All decisions from VectorDB (via get_decisions()).
            Each dict should have: id, superseded_by, and metadata.serves_capabilities.

        entities: All entities from VectorDB (via get_entities()).
            Each dict should have: id, and optionally referenced_by in metadata.

        stories: All stories from Backlog.md (via task_list()).
            Each dict should have: id, labels (list of strings).

    Returns:
        ArchitectureDiff with computed lists of what needs attention.

    Note:
        All inputs are dicts, not dataclasses:
        - capabilities/decisions/entities: VectorDB returns dicts
        - stories: Backlog.md task_list returns dicts

    Example:
        >>> caps = [{"id": "CAP-F-001"}, {"id": "CAP-F-002"}]
        >>> decs = [{"id": "DEC-001", "metadata": {"serves_capabilities": ["CAP-F-001"]}}]
        >>> diff = compute_architecture_diff(caps, decs, [], [])
        >>> diff.uncovered_capabilities
        ['CAP-F-002']
    """

    # 1. Identify superseded vs active capabilities
    superseded_cap_ids = {c["id"] for c in capabilities if c.get("superseded_by")}
    active_cap_ids = {c["id"] for c in capabilities if not c.get("superseded_by")}

    # 2. Find capabilities not served by any active decision
    served_cap_ids = set()
    for d in decisions:
        if not d.get("superseded_by"):  # Only count active decisions
            # serves_capabilities is in metadata
            serves = d.get("metadata", {}).get("serves_capabilities", [])
            # Also check top-level for backwards compatibility
            if not serves:
                serves = d.get("serves_capabilities", [])
            served_cap_ids.update(serves)

    uncovered = active_cap_ids - served_cap_ids

    # 3. Find decisions affected by superseded capabilities
    # (decisions that serve capabilities that have been superseded)
    affected_decision_ids = []
    for d in decisions:
        if d.get("superseded_by"):
            continue  # Skip already-superseded decisions

        serves = d.get("metadata", {}).get("serves_capabilities", [])
        if not serves:
            serves = d.get("serves_capabilities", [])

        # Check if any served capability is superseded
        if any(cap_id in superseded_cap_ids for cap_id in serves):
            affected_decision_ids.append(d["id"])

    # 4. Find entities referenced by affected decisions
    # Entities may have a "referenced_by" field in metadata tracking which decisions use them
    affected_entity_ids = []
    for e in entities:
        if e.get("superseded_by"):
            continue  # Skip superseded entities

        # Check if entity is referenced by any affected decision
        referenced_by = e.get("metadata", {}).get("referenced_by", [])
        if not referenced_by:
            referenced_by = e.get("referenced_by", [])

        if any(dec_id in affected_decision_ids for dec_id in referenced_by):
            affected_entity_ids.append(e["id"])

    # 5. Find stories implementing superseded capabilities
    # Stories are dicts from Backlog.md task_list with "labels" key
    affected_story_ids = []
    # Also track which capabilities have stories
    caps_with_stories = set()
    for s in stories:
        labels = s.get("labels", [])
        # Check for "implements:CAP-*" labels
        for label in labels:
            if label.startswith("implements:"):
                cap_id = label.replace("implements:", "")
                caps_with_stories.add(cap_id)
                # Check if this story implements a superseded capability
                if cap_id in superseded_cap_ids:
                    affected_story_ids.append(s["id"])
                    break  # Only add once per story

    # 6. Find capabilities with decisions but no stories
    # These are capabilities that have been addressed by architecture decisions
    # but don't have implementation stories yet
    caps_without_stories = served_cap_ids - caps_with_stories
    # Only include active (non-superseded) capabilities
    caps_without_stories = caps_without_stories & active_cap_ids

    return ArchitectureDiff(
        uncovered_capabilities=sorted(uncovered),
        capabilities_without_stories=sorted(caps_without_stories),
        affected_decisions=sorted(affected_decision_ids),
        affected_entities=sorted(affected_entity_ids),
        affected_stories=sorted(affected_story_ids),
    )


def get_diff_context_for_prompt(diff: ArchitectureDiff) -> str:
    """Format the diff as context for an LLM prompt.

    This provides a structured summary that can be injected into
    agent prompts to guide their behavior.

    Args:
        diff: The computed architecture diff

    Returns:
        Formatted string for inclusion in prompts
    """
    if diff.is_empty():
        return "**Architecture Status:** No changes needed. All capabilities are covered."

    lines = ["**Architecture Diff (What Needs Attention):**", ""]

    if diff.uncovered_capabilities:
        lines.append(f"**Uncovered Capabilities ({len(diff.uncovered_capabilities)}):**")
        lines.append("These capabilities need architecture decisions:")
        for cap_id in diff.uncovered_capabilities:
            lines.append(f"  - {cap_id}")
        lines.append("")

    if diff.capabilities_without_stories:
        lines.append(
            f"**Capabilities Without Stories ({len(diff.capabilities_without_stories)}):**"
        )
        lines.append("These capabilities have decisions but need implementation stories:")
        for cap_id in diff.capabilities_without_stories:
            lines.append(f"  - {cap_id}")
        lines.append("")

    if diff.affected_decisions:
        lines.append(f"**Affected Decisions ({len(diff.affected_decisions)}):**")
        lines.append("These decisions serve superseded capabilities and may need revision:")
        for dec_id in diff.affected_decisions:
            lines.append(f"  - {dec_id}")
        lines.append("")

    if diff.affected_entities:
        lines.append(f"**Affected Entities ({len(diff.affected_entities)}):**")
        lines.append("These entities may need updates:")
        for ent_id in diff.affected_entities:
            lines.append(f"  - {ent_id}")
        lines.append("")

    if diff.affected_stories:
        lines.append(f"**Affected Stories ({len(diff.affected_stories)}):**")
        lines.append("These stories implement superseded capabilities and need review:")
        for story_id in diff.affected_stories:
            lines.append(f"  - {story_id}")
        lines.append("")

    return "\n".join(lines)
