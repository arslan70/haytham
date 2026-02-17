"""Tests for Workflow 2 Architecture Diff computation.

These tests verify the core algorithm from ADR-005 that determines
what architect agents need to address.
"""

from haytham.phases.workflow_2.diff import (
    ArchitectureDiff,
    compute_architecture_diff,
    get_diff_context_for_prompt,
)


class TestArchitectureDiff:
    """Tests for the ArchitectureDiff dataclass."""

    def test_empty_diff(self):
        """Empty diff should report nothing to do."""
        diff = ArchitectureDiff()
        assert diff.is_empty()
        assert not diff.is_greenfield()
        assert not diff.has_revisions_needed()
        assert diff.summary() == "No architecture changes needed"

    def test_greenfield_diff(self):
        """Diff with only uncovered capabilities is greenfield."""
        diff = ArchitectureDiff(uncovered_capabilities=["CAP-F-001", "CAP-F-002"])
        assert not diff.is_empty()
        assert diff.is_greenfield()
        assert not diff.has_revisions_needed()
        assert "2 uncovered capabilities" in diff.summary()

    def test_revision_diff(self):
        """Diff with affected decisions needs revision."""
        diff = ArchitectureDiff(
            affected_decisions=["DEC-001"],
            affected_entities=["ENT-001"],
        )
        assert not diff.is_empty()
        assert not diff.is_greenfield()
        assert diff.has_revisions_needed()
        assert "1 affected decisions" in diff.summary()
        assert "1 affected entities" in diff.summary()

    def test_mixed_diff(self):
        """Diff with both uncovered and affected items."""
        diff = ArchitectureDiff(
            uncovered_capabilities=["CAP-F-003"],
            affected_decisions=["DEC-001"],
            affected_stories=["STORY-001", "STORY-002"],
        )
        assert not diff.is_empty()
        assert not diff.is_greenfield()  # Has affected decisions
        assert diff.has_revisions_needed()


class TestComputeArchitectureDiff:
    """Tests for compute_architecture_diff() function."""

    def test_empty_inputs(self):
        """Empty inputs should produce empty diff."""
        diff = compute_architecture_diff([], [], [], [])
        assert diff.is_empty()

    def test_all_capabilities_covered(self):
        """When all capabilities are covered, no uncovered list."""
        capabilities = [
            {"id": "CAP-F-001"},
            {"id": "CAP-F-002"},
        ]
        decisions = [
            {"id": "DEC-001", "metadata": {"serves_capabilities": ["CAP-F-001", "CAP-F-002"]}}
        ]

        diff = compute_architecture_diff(capabilities, decisions, [], [])

        assert diff.uncovered_capabilities == []
        assert diff.is_empty()

    def test_uncovered_capabilities(self):
        """Capabilities not served by any decision should be uncovered."""
        capabilities = [
            {"id": "CAP-F-001"},
            {"id": "CAP-F-002"},
            {"id": "CAP-F-003"},  # Not covered
        ]
        decisions = [
            {"id": "DEC-001", "metadata": {"serves_capabilities": ["CAP-F-001", "CAP-F-002"]}}
        ]

        diff = compute_architecture_diff(capabilities, decisions, [], [])

        assert diff.uncovered_capabilities == ["CAP-F-003"]

    def test_superseded_capabilities_not_counted(self):
        """Superseded capabilities should not appear as uncovered."""
        capabilities = [
            {"id": "CAP-F-001"},
            {"id": "CAP-F-002", "superseded_by": "CAP-F-002-v2"},  # Superseded
            {"id": "CAP-F-002-v2"},  # New version
        ]
        decisions = [{"id": "DEC-001", "metadata": {"serves_capabilities": ["CAP-F-001"]}}]

        diff = compute_architecture_diff(capabilities, decisions, [], [])

        # CAP-F-002 is superseded so not counted
        # CAP-F-002-v2 is new and uncovered
        assert "CAP-F-002" not in diff.uncovered_capabilities
        assert "CAP-F-002-v2" in diff.uncovered_capabilities

    def test_affected_decisions(self):
        """Decisions serving superseded capabilities should be affected."""
        capabilities = [
            {"id": "CAP-F-001", "superseded_by": "CAP-F-001-v2"},  # Superseded
            {"id": "CAP-F-001-v2"},  # New version
            {"id": "CAP-F-002"},
        ]
        decisions = [
            {
                "id": "DEC-001",
                "metadata": {
                    "serves_capabilities": ["CAP-F-001", "CAP-F-002"]
                },  # Serves superseded
            },
            {
                "id": "DEC-002",
                "metadata": {"serves_capabilities": ["CAP-F-002"]},  # Only serves active
            },
        ]

        diff = compute_architecture_diff(capabilities, decisions, [], [])

        assert "DEC-001" in diff.affected_decisions
        assert "DEC-002" not in diff.affected_decisions

    def test_superseded_decisions_not_affected(self):
        """Already-superseded decisions should not appear as affected."""
        capabilities = [
            {"id": "CAP-F-001", "superseded_by": "CAP-F-001-v2"},
        ]
        decisions = [
            {
                "id": "DEC-001",
                "superseded_by": "DEC-002",  # Already superseded
                "metadata": {"serves_capabilities": ["CAP-F-001"]},
            }
        ]

        diff = compute_architecture_diff(capabilities, decisions, [], [])

        assert "DEC-001" not in diff.affected_decisions

    def test_affected_entities(self):
        """Entities referenced by affected decisions should be affected."""
        capabilities = [
            {"id": "CAP-F-001", "superseded_by": "CAP-F-001-v2"},
        ]
        decisions = [{"id": "DEC-001", "metadata": {"serves_capabilities": ["CAP-F-001"]}}]
        entities = [
            {
                "id": "ENT-001",
                "metadata": {"referenced_by": ["DEC-001"]},  # Referenced by affected decision
            },
            {
                "id": "ENT-002",
                "metadata": {"referenced_by": ["DEC-002"]},  # Not affected
            },
        ]

        diff = compute_architecture_diff(capabilities, decisions, entities, [])

        assert "ENT-001" in diff.affected_entities
        assert "ENT-002" not in diff.affected_entities

    def test_affected_stories(self):
        """Stories implementing superseded capabilities should be affected."""
        capabilities = [
            {"id": "CAP-F-001", "superseded_by": "CAP-F-001-v2"},
            {"id": "CAP-F-002"},
        ]
        stories = [
            {
                "id": "STORY-001",
                "labels": ["implements:CAP-F-001"],  # Implements superseded
            },
            {
                "id": "STORY-002",
                "labels": ["implements:CAP-F-002"],  # Implements active
            },
            {
                "id": "STORY-003",
                "labels": ["implements:CAP-F-001", "implements:CAP-F-002"],  # Both
            },
        ]

        diff = compute_architecture_diff(capabilities, [], [], stories)

        assert "STORY-001" in diff.affected_stories
        assert "STORY-002" not in diff.affected_stories
        assert "STORY-003" in diff.affected_stories  # Has at least one superseded

    def test_adr_example_uncovered_computation(self):
        """Test the example from ADR-005 documentation."""
        # From ADR-005:
        # Capabilities (active):
        #   - CAP-F-001 (Quick Capture)
        #   - CAP-F-002 (Note Retrieval)
        #   - CAP-F-003-v2 (Authenticated Sharing) ← NEW
        #   - CAP-NF-001 (Response Time)
        #
        # Decisions (active):
        #   - DEC-001 serves [CAP-F-001, CAP-F-002]
        #   - DEC-002 serves [CAP-F-002]
        #   - DEC-003 serves [CAP-F-001, CAP-F-002, CAP-NF-001]
        #
        # Result: CAP-F-003-v2 is uncovered

        capabilities = [
            {"id": "CAP-F-001"},
            {"id": "CAP-F-002"},
            {"id": "CAP-F-003-v2"},  # NEW - not covered
            {"id": "CAP-NF-001"},
        ]
        decisions = [
            {"id": "DEC-001", "metadata": {"serves_capabilities": ["CAP-F-001", "CAP-F-002"]}},
            {"id": "DEC-002", "metadata": {"serves_capabilities": ["CAP-F-002"]}},
            {
                "id": "DEC-003",
                "metadata": {"serves_capabilities": ["CAP-F-001", "CAP-F-002", "CAP-NF-001"]},
            },
        ]

        diff = compute_architecture_diff(capabilities, decisions, [], [])

        assert diff.uncovered_capabilities == ["CAP-F-003-v2"]
        assert diff.affected_decisions == []

    def test_serves_capabilities_top_level_fallback(self):
        """serves_capabilities at top level should work (backwards compat)."""
        capabilities = [{"id": "CAP-F-001"}, {"id": "CAP-F-002"}]
        decisions = [
            {
                "id": "DEC-001",
                "serves_capabilities": ["CAP-F-001"],  # Top-level, not in metadata
            }
        ]

        diff = compute_architecture_diff(capabilities, decisions, [], [])

        # CAP-F-001 is covered, CAP-F-002 is not
        assert "CAP-F-001" not in diff.uncovered_capabilities
        assert "CAP-F-002" in diff.uncovered_capabilities


class TestGetDiffContextForPrompt:
    """Tests for prompt context generation."""

    def test_empty_diff_context(self):
        """Empty diff should produce simple message."""
        diff = ArchitectureDiff()
        context = get_diff_context_for_prompt(diff)
        assert "No changes needed" in context

    def test_uncovered_context(self):
        """Uncovered capabilities should appear in context."""
        diff = ArchitectureDiff(uncovered_capabilities=["CAP-F-001"])
        context = get_diff_context_for_prompt(diff)
        assert "Uncovered Capabilities" in context
        assert "CAP-F-001" in context

    def test_affected_context(self):
        """All affected items should appear in context."""
        diff = ArchitectureDiff(
            affected_decisions=["DEC-001"],
            affected_entities=["ENT-001"],
            affected_stories=["STORY-001"],
        )
        context = get_diff_context_for_prompt(diff)
        assert "Affected Decisions" in context
        assert "Affected Entities" in context
        assert "Affected Stories" in context
