"""Supersession and Change Management.

This module handles the change management workflow when capabilities are superseded.
When a capability is superseded (replaced by a new version), all artifacts that
reference it need to be reviewed:

- Decisions that serve the capability
- Stories that implement the capability
- Entities that were designed for the capability

Key concepts:
- Supersession: When a capability is replaced by a new version (CAP-F-001 → CAP-F-001-v2)
- Affected: An artifact that references a superseded capability
- Review label: `needs-review:superseded` - tag for stories needing manual review

This is critical for maintaining traceability as defined in ADR-005.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SupersededCapability:
    """A capability that has been superseded."""

    id: str
    name: str
    superseded_by: str
    superseded_at: str = None


@dataclass
class AffectedStory:
    """A story that references a superseded capability."""

    story_id: str
    title: str
    capability_ids: list[str]  # The superseded CAP-* IDs it implements
    current_labels: list[str]
    needs_review_added: bool = False


@dataclass
class AffectedDecision:
    """A decision that serves a superseded capability."""

    decision_id: str
    name: str
    capability_ids: list[str]  # The superseded CAP-* IDs it serves


@dataclass
class AffectedEntity:
    """An entity referenced by affected decisions."""

    entity_id: str
    name: str
    referenced_by: list[str]  # Decision IDs


@dataclass
class ChangeImpactReport:
    """Full report of artifacts affected by superseded capabilities."""

    # Superseded capabilities
    superseded_capabilities: list[SupersededCapability] = field(default_factory=list)

    # Affected artifacts
    affected_stories: list[AffectedStory] = field(default_factory=list)
    affected_decisions: list[AffectedDecision] = field(default_factory=list)
    affected_entities: list[AffectedEntity] = field(default_factory=list)

    # Stats
    total_superseded: int = 0
    total_affected_stories: int = 0
    total_affected_decisions: int = 0
    total_affected_entities: int = 0

    # Status
    needs_attention: bool = False
    review_labels_added: int = 0
    generated_at: str = None

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat() + "Z"

    @property
    def has_affected_artifacts(self) -> bool:
        return (
            len(self.affected_stories) > 0
            or len(self.affected_decisions) > 0
            or len(self.affected_entities) > 0
        )


def find_superseded_capabilities(session_manager) -> list[SupersededCapability]:
    """Find all superseded capabilities in VectorDB.

    Args:
        session_manager: SessionManager instance

    Returns:
        List of SupersededCapability objects
    """
    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        return []

    db = SystemStateDB(str(db_path))
    capabilities = db.get_capabilities()

    superseded = []
    for cap in capabilities:
        if cap.get("superseded_by"):
            superseded.append(
                SupersededCapability(
                    id=cap.get("id", ""),
                    name=cap.get("name", "Unknown"),
                    superseded_by=cap.get("superseded_by"),
                    superseded_at=cap.get("updated_at"),
                )
            )

    return superseded


def find_affected_stories(
    session_manager,
    superseded_cap_ids: list[str],
) -> list[AffectedStory]:
    """Find stories that implement superseded capabilities.

    Args:
        session_manager: SessionManager instance
        superseded_cap_ids: List of superseded capability IDs

    Returns:
        List of AffectedStory objects
    """
    if not superseded_cap_ids:
        return []

    # Build a set for fast lookup
    superseded_set = set(superseded_cap_ids)

    # Try to load stories from Backlog.md
    tasks = []
    try:
        from haytham.backlog import BacklogCLI

        cli = BacklogCLI(session_manager.session_dir.parent)
        if cli.is_initialized():
            tasks = cli.list_tasks()
    except ImportError:
        logger.warning("BacklogCLI not available")
        return []
    except Exception as e:
        logger.warning(f"Could not load stories: {e}")
        return []

    # Find affected stories
    affected = []
    for task in tasks:
        labels = task.labels

        # Check for implements: labels that reference superseded capabilities
        implementing_superseded = []
        for label in labels:
            if label.startswith("implements:"):
                cap_id = label.replace("implements:", "")
                if cap_id in superseded_set:
                    implementing_superseded.append(cap_id)

        if implementing_superseded:
            affected.append(
                AffectedStory(
                    story_id=task.id,
                    title=task.title,
                    capability_ids=implementing_superseded,
                    current_labels=labels,
                    needs_review_added="needs-review:superseded" in labels,
                )
            )

    return affected


def find_affected_decisions(
    session_manager,
    superseded_cap_ids: list[str],
) -> list[AffectedDecision]:
    """Find decisions that serve superseded capabilities.

    Args:
        session_manager: SessionManager instance
        superseded_cap_ids: List of superseded capability IDs

    Returns:
        List of AffectedDecision objects
    """
    if not superseded_cap_ids:
        return []

    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        return []

    db = SystemStateDB(str(db_path))
    decisions = db.get_decisions()

    superseded_set = set(superseded_cap_ids)
    affected = []

    for dec in decisions:
        if dec.get("superseded_by"):
            continue  # Skip already-superseded decisions

        serves = dec.get("metadata", {}).get("serves_capabilities", [])
        if not serves:
            serves = dec.get("serves_capabilities", [])

        serving_superseded = [cap_id for cap_id in serves if cap_id in superseded_set]

        if serving_superseded:
            affected.append(
                AffectedDecision(
                    decision_id=dec.get("id", ""),
                    name=dec.get("name", "Unknown"),
                    capability_ids=serving_superseded,
                )
            )

    return affected


def find_affected_entities(
    session_manager,
    affected_decision_ids: list[str],
) -> list[AffectedEntity]:
    """Find entities referenced by affected decisions.

    Args:
        session_manager: SessionManager instance
        affected_decision_ids: List of affected decision IDs

    Returns:
        List of AffectedEntity objects
    """
    if not affected_decision_ids:
        return []

    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        return []

    db = SystemStateDB(str(db_path))
    entities = db.get_entities()

    decision_set = set(affected_decision_ids)
    affected = []

    for ent in entities:
        if ent.get("superseded_by"):
            continue

        referenced_by = ent.get("metadata", {}).get("referenced_by", [])
        if not referenced_by:
            referenced_by = ent.get("referenced_by", [])

        referencing_affected = [dec_id for dec_id in referenced_by if dec_id in decision_set]

        if referencing_affected:
            affected.append(
                AffectedEntity(
                    entity_id=ent.get("id", ""),
                    name=ent.get("name", "Unknown"),
                    referenced_by=referencing_affected,
                )
            )

    return affected


def compute_change_impact(session_manager) -> ChangeImpactReport:
    """Compute the full change impact from superseded capabilities.

    This is the main entry point for change management analysis.

    Args:
        session_manager: SessionManager instance

    Returns:
        ChangeImpactReport with all affected artifacts
    """
    logger.info("Computing change impact from superseded capabilities...")

    # 1. Find superseded capabilities
    superseded = find_superseded_capabilities(session_manager)
    superseded_ids = [s.id for s in superseded]

    if not superseded:
        logger.info("No superseded capabilities found")
        return ChangeImpactReport(needs_attention=False)

    logger.info(f"Found {len(superseded)} superseded capabilities")

    # 2. Find affected stories
    affected_stories = find_affected_stories(session_manager, superseded_ids)

    # 3. Find affected decisions
    affected_decisions = find_affected_decisions(session_manager, superseded_ids)
    affected_decision_ids = [d.decision_id for d in affected_decisions]

    # 4. Find affected entities
    affected_entities = find_affected_entities(session_manager, affected_decision_ids)

    logger.info(
        f"Change impact: {len(affected_stories)} stories, "
        f"{len(affected_decisions)} decisions, {len(affected_entities)} entities"
    )

    return ChangeImpactReport(
        superseded_capabilities=superseded,
        affected_stories=affected_stories,
        affected_decisions=affected_decisions,
        affected_entities=affected_entities,
        total_superseded=len(superseded),
        total_affected_stories=len(affected_stories),
        total_affected_decisions=len(affected_decisions),
        total_affected_entities=len(affected_entities),
        needs_attention=len(affected_stories) > 0 or len(affected_decisions) > 0,
    )


def add_review_labels_to_stories(
    session_manager,
    affected_stories: list[AffectedStory],
) -> int:
    """Add 'needs-review:superseded' label to affected stories.

    Args:
        session_manager: SessionManager instance
        affected_stories: Stories that need the review label

    Returns:
        Number of stories updated
    """
    if not affected_stories:
        return 0

    updated = 0

    try:
        from haytham.backlog import BacklogCLI

        cli = BacklogCLI(session_manager.session_dir.parent)

        if not cli.is_initialized():
            logger.warning("Backlog not initialized, cannot add labels")
            return 0

        for story in affected_stories:
            if story.needs_review_added:
                continue  # Already has the label

            # Add the review label via CLI
            if hasattr(cli, "add_label"):
                try:
                    cli.add_label(story.story_id, "needs-review:superseded")
                    updated += 1
                    logger.info(f"Added needs-review:superseded to {story.story_id}")
                except Exception as e:
                    logger.error(f"Failed to add label to {story.story_id}: {e}")
            else:
                logger.warning("BacklogCLI does not have add_label method")
                break

    except Exception as e:
        logger.error(f"Failed to add review labels: {e}")

    return updated


def format_change_impact_report(report: ChangeImpactReport) -> str:
    """Format change impact report as markdown.

    Args:
        report: ChangeImpactReport to format

    Returns:
        Markdown string for display
    """
    lines = ["# Change Impact Report\n"]

    # Status banner
    if not report.needs_attention:
        lines.append("✅ **No changes require attention.**\n")
        lines.append("All capabilities are current — no superseded capabilities found.\n")
        return "\n".join(lines)

    lines.append("⚠️ **Changes detected that may require review.**\n")

    # Summary
    lines.append("## Summary\n")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Superseded Capabilities | {report.total_superseded} |")
    lines.append(f"| Affected Stories | {report.total_affected_stories} |")
    lines.append(f"| Affected Decisions | {report.total_affected_decisions} |")
    lines.append(f"| Affected Entities | {report.total_affected_entities} |")
    lines.append("")

    # Superseded capabilities
    if report.superseded_capabilities:
        lines.append("## Superseded Capabilities\n")
        lines.append("These capabilities have been replaced by newer versions:\n")
        for cap in report.superseded_capabilities:
            lines.append(f"- **{cap.id}**: {cap.name} → *{cap.superseded_by}*")
        lines.append("")

    # Affected stories
    if report.affected_stories:
        lines.append("## ⚠️ Stories Needing Review\n")
        lines.append("These stories implement superseded capabilities and may need updates:\n")
        for story in report.affected_stories:
            review_status = "✅ labeled" if story.needs_review_added else "❌ not labeled"
            caps = ", ".join(story.capability_ids)
            lines.append(f"- **{story.story_id}**: {story.title}")
            lines.append(f"  - Implements: {caps}")
            lines.append(f"  - Review status: {review_status}")
        lines.append("")

    # Affected decisions
    if report.affected_decisions:
        lines.append("## ⚠️ Decisions Needing Review\n")
        lines.append("These decisions serve superseded capabilities:\n")
        for dec in report.affected_decisions:
            caps = ", ".join(dec.capability_ids)
            lines.append(f"- **{dec.decision_id}**: {dec.name}")
            lines.append(f"  - Serves: {caps}")
        lines.append("")

    # Affected entities
    if report.affected_entities:
        lines.append("## Potentially Affected Entities\n")
        lines.append("These entities may need review based on affected decisions:\n")
        for ent in report.affected_entities:
            refs = ", ".join(ent.referenced_by)
            lines.append(f"- **{ent.entity_id}**: {ent.name} (via {refs})")
        lines.append("")

    # Recommendations
    lines.append("## Recommended Actions\n")
    lines.append("1. Review affected stories and update `implements:` labels if needed\n")
    lines.append("2. Consider superseding affected decisions with updated versions\n")
    lines.append("3. Run Technical Translation to generate stories for new capabilities\n")

    return "\n".join(lines)


def get_change_summary(session_manager) -> dict:
    """Get a quick change impact summary.

    Args:
        session_manager: SessionManager instance

    Returns:
        Dict with key impact metrics
    """
    report = compute_change_impact(session_manager)

    return {
        "superseded_count": report.total_superseded,
        "affected_stories": report.total_affected_stories,
        "affected_decisions": report.total_affected_decisions,
        "affected_entities": report.total_affected_entities,
        "needs_attention": report.needs_attention,
        "generated_at": report.generated_at,
    }
