"""Capability Coverage Analysis.

This module provides functions to analyze and report on capability coverage,
showing which capabilities have decisions, which have stories, and which
are fully tracked through the development lifecycle.

Key concepts:
- Coverage: A capability is "covered" if it has at least one story with
  an `implements:CAP-*` label.
- Decision coverage: A capability is "decision-covered" if at least one
  decision has it in serves_capabilities.
- Full coverage: Both decision AND story coverage.

This is a key output of Workflow 2 (Technical Translation) as defined in ADR-005.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CapabilityCoverage:
    """Coverage status for a single capability."""

    capability_id: str
    capability_name: str
    capability_type: str  # "functional", "non_functional", "operational"

    # Decision coverage
    decisions: list[str] = field(default_factory=list)  # DEC-* IDs
    has_decision: bool = False

    # Story coverage
    stories: list[str] = field(default_factory=list)  # Story IDs
    has_story: bool = False

    # Overall status
    is_covered: bool = False  # Has at least one story
    is_fully_covered: bool = False  # Has decision AND story

    # Supersession status
    is_superseded: bool = False
    superseded_by: str = None


@dataclass
class CoverageReport:
    """Overall coverage report for all capabilities."""

    # All capabilities
    total_capabilities: int = 0
    functional_count: int = 0
    non_functional_count: int = 0
    operational_count: int = 0

    # Coverage stats
    covered_count: int = 0  # Has story
    decision_covered_count: int = 0  # Has decision
    fully_covered_count: int = 0  # Has both
    uncovered_count: int = 0  # Has neither

    # Supersession stats
    superseded_count: int = 0

    # Detailed breakdown
    capabilities: list[CapabilityCoverage] = field(default_factory=list)

    # Convenience accessors
    @property
    def coverage_percentage(self) -> float:
        """Percentage of capabilities with at least one story."""
        if self.total_capabilities == 0:
            return 100.0
        # Don't count superseded in the denominator
        active = self.total_capabilities - self.superseded_count
        if active == 0:
            return 100.0
        return (self.covered_count / active) * 100

    @property
    def decision_coverage_percentage(self) -> float:
        """Percentage of capabilities with at least one decision."""
        if self.total_capabilities == 0:
            return 100.0
        active = self.total_capabilities - self.superseded_count
        if active == 0:
            return 100.0
        return (self.decision_covered_count / active) * 100

    @property
    def full_coverage_percentage(self) -> float:
        """Percentage of capabilities with both decision and story."""
        if self.total_capabilities == 0:
            return 100.0
        active = self.total_capabilities - self.superseded_count
        if active == 0:
            return 100.0
        return (self.fully_covered_count / active) * 100

    def get_uncovered_capabilities(self) -> list[CapabilityCoverage]:
        """Get list of capabilities with no stories."""
        return [c for c in self.capabilities if not c.is_covered and not c.is_superseded]

    def get_decision_gaps(self) -> list[CapabilityCoverage]:
        """Get capabilities with stories but no decisions."""
        return [
            c
            for c in self.capabilities
            if c.has_story and not c.has_decision and not c.is_superseded
        ]

    def get_story_gaps(self) -> list[CapabilityCoverage]:
        """Get capabilities with decisions but no stories."""
        return [
            c
            for c in self.capabilities
            if c.has_decision and not c.has_story and not c.is_superseded
        ]


def get_capability_coverage(
    session_manager,
    include_superseded: bool = True,
) -> CoverageReport:
    """Compute capability coverage from VectorDB and Backlog.md.

    This function:
    1. Loads all capabilities from VectorDB
    2. Loads all decisions to find which capabilities they serve
    3. Loads all stories to find which capabilities they implement
    4. Computes coverage status for each capability

    Args:
        session_manager: SessionManager instance for accessing VectorDB
        include_superseded: Whether to include superseded capabilities in report

    Returns:
        CoverageReport with full coverage analysis
    """
    logger.info("Computing capability coverage...")

    # 1. Load capabilities from VectorDB
    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        logger.warning("VectorDB not found, returning empty coverage report")
        return CoverageReport()

    db = SystemStateDB(str(db_path))

    capabilities = db.get_capabilities()
    decisions = db.get_decisions()

    logger.info(f"Loaded {len(capabilities)} capabilities, {len(decisions)} decisions")

    # 2. Build decision -> capability mapping
    decision_serves: dict[str, set[str]] = {}  # cap_id -> set of dec_ids
    for dec in decisions:
        if dec.get("superseded_by"):
            continue  # Skip superseded decisions

        dec_id = dec.get("id", "")
        serves = dec.get("metadata", {}).get("serves_capabilities", [])
        if not serves:
            serves = dec.get("serves_capabilities", [])

        for cap_id in serves:
            if cap_id not in decision_serves:
                decision_serves[cap_id] = set()
            decision_serves[cap_id].add(dec_id)

    # 3. Load stories from Backlog.md
    story_implements: dict[str, list[str]] = {}  # cap_id -> list of story ids
    story_status: dict[str, str] = {}  # story_id -> status

    try:
        from haytham.backlog import BacklogCLI

        cli = BacklogCLI(session_manager.session_dir.parent)
        if cli.is_initialized():
            # Get all tasks using list_tasks()
            tasks = cli.list_tasks()
            for task in tasks:
                story_id = task.id
                story_status[story_id] = task.status
                for label in task.labels:
                    if label.startswith("implements:"):
                        cap_id = label.replace("implements:", "")
                        if cap_id not in story_implements:
                            story_implements[cap_id] = []
                        story_implements[cap_id].append(story_id)
            logger.info(
                f"Found {len(story_implements)} capabilities with stories from {len(tasks)} tasks"
            )
    except ImportError:
        logger.warning("BacklogCLI not available")
    except Exception as e:
        logger.warning(f"Could not load stories from Backlog.md: {e}")

    # 4. Compute coverage for each capability
    report = CoverageReport()
    report.total_capabilities = len(capabilities)

    for cap in capabilities:
        cap_id = cap.get("id", "")
        cap_name = cap.get("name", "Unknown")
        cap_type = cap.get("subtype", "functional")

        # Count by type
        if cap_type == "functional":
            report.functional_count += 1
        elif cap_type == "non_functional":
            report.non_functional_count += 1
        elif cap_type == "operational":
            report.operational_count += 1

        # Create coverage entry
        coverage = CapabilityCoverage(
            capability_id=cap_id,
            capability_name=cap_name,
            capability_type=cap_type,
        )

        # Check supersession
        if cap.get("superseded_by"):
            coverage.is_superseded = True
            coverage.superseded_by = cap["superseded_by"]
            report.superseded_count += 1

        # Check decision coverage
        if cap_id in decision_serves:
            coverage.decisions = list(decision_serves[cap_id])
            coverage.has_decision = True
            report.decision_covered_count += 1

        # Check story coverage
        if cap_id in story_implements:
            coverage.stories = story_implements[cap_id]
            coverage.has_story = True
            report.covered_count += 1

        # Compute overall status
        coverage.is_covered = coverage.has_story
        coverage.is_fully_covered = coverage.has_decision and coverage.has_story

        if coverage.is_fully_covered:
            report.fully_covered_count += 1
        elif not coverage.has_story and not coverage.is_superseded:
            report.uncovered_count += 1

        # Add to report (optionally skip superseded)
        if include_superseded or not coverage.is_superseded:
            report.capabilities.append(coverage)

    logger.info(
        f"Coverage computed: {report.covered_count}/{report.total_capabilities} covered ({report.coverage_percentage:.1f}%)"
    )

    return report


def format_coverage_report(report: CoverageReport) -> str:
    """Format coverage report as markdown for display.

    Args:
        report: CoverageReport to format

    Returns:
        Markdown string for display
    """
    lines = ["# Capability Coverage Report\n"]

    # Summary
    lines.append("## Summary\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Capabilities | {report.total_capabilities} |")
    lines.append(f"| Functional | {report.functional_count} |")
    lines.append(f"| Non-Functional | {report.non_functional_count} |")
    lines.append(f"| Operational | {report.operational_count} |")
    lines.append(f"| Superseded | {report.superseded_count} |")
    lines.append("")

    # Coverage stats
    lines.append("## Coverage Status\n")
    lines.append("| Coverage Type | Count | Percentage |")
    lines.append("|---------------|-------|------------|")
    lines.append(
        f"| Has Story (Covered) | {report.covered_count} | {report.coverage_percentage:.1f}% |"
    )
    lines.append(
        f"| Has Decision | {report.decision_covered_count} | {report.decision_coverage_percentage:.1f}% |"
    )
    lines.append(
        f"| Fully Covered (Both) | {report.fully_covered_count} | {report.full_coverage_percentage:.1f}% |"
    )
    lines.append(f"| Uncovered | {report.uncovered_count} | - |")
    lines.append("")

    # Uncovered capabilities (if any)
    uncovered = report.get_uncovered_capabilities()
    if uncovered:
        lines.append("## ⚠️ Uncovered Capabilities\n")
        lines.append("These capabilities have no stories implementing them:\n")
        for cap in uncovered:
            dec_info = f" (decisions: {', '.join(cap.decisions)})" if cap.decisions else ""
            lines.append(f"- **{cap.capability_id}**: {cap.capability_name}{dec_info}")
        lines.append("")

    # Decision gaps (have stories but no decisions)
    decision_gaps = report.get_decision_gaps()
    if decision_gaps:
        lines.append("## ⚠️ Missing Decisions\n")
        lines.append("These capabilities have stories but no architecture decisions:\n")
        for cap in decision_gaps:
            lines.append(
                f"- **{cap.capability_id}**: {cap.capability_name} (stories: {len(cap.stories)})"
            )
        lines.append("")

    # Story gaps (have decisions but no stories)
    story_gaps = report.get_story_gaps()
    if story_gaps:
        lines.append("## ⚠️ Missing Stories\n")
        lines.append("These capabilities have decisions but no implementation stories:\n")
        for cap in story_gaps:
            lines.append(
                f"- **{cap.capability_id}**: {cap.capability_name} (decisions: {', '.join(cap.decisions)})"
            )
        lines.append("")

    # Fully covered (if any)
    fully_covered = [c for c in report.capabilities if c.is_fully_covered]
    if fully_covered:
        lines.append("## ✅ Fully Covered Capabilities\n")
        lines.append("These capabilities have both decisions and stories:\n")
        for cap in fully_covered[:10]:  # Limit to first 10
            lines.append(f"- **{cap.capability_id}**: {cap.capability_name}")
        if len(fully_covered) > 10:
            lines.append(f"\n*...and {len(fully_covered) - 10} more*")
        lines.append("")

    # Success message if fully covered
    if report.uncovered_count == 0 and report.total_capabilities > 0:
        lines.append("---\n")
        lines.append("🎉 **All capabilities are covered by stories!**")

    return "\n".join(lines)


def get_coverage_summary(session_manager) -> dict:
    """Get a simple coverage summary dict for quick checks.

    Args:
        session_manager: SessionManager instance

    Returns:
        Dict with key coverage metrics
    """
    report = get_capability_coverage(session_manager)

    return {
        "total": report.total_capabilities,
        "covered": report.covered_count,
        "uncovered": report.uncovered_count,
        "coverage_percentage": round(report.coverage_percentage, 1),
        "fully_covered": report.fully_covered_count,
        "needs_attention": report.uncovered_count > 0,
    }
