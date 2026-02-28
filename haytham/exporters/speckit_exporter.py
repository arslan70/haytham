"""Spec Kit directory tree exporter.

Produces the .specify/ structure consumed by AI coding agents via the
github/spec-kit toolchain. The tree layout:

    .specify/
    +-- memory/
    |   +-- constitution.md
    +-- specs/
        +-- 001-user-authentication/
        |   +-- spec.md
        |   +-- plan.md
        |   +-- tasks.md
        |   +-- data-model.md        (only if layer 2 stories exist)
        |   +-- contracts/
        |       +-- api.md           (only if layer 3 stories exist)
        +-- ...
"""

from haytham.exporters.project_exporter_base import ProjectExporter
from haytham.exporters.project_model import (
    ExportableCapability,
    ExportableProject,
    ExportableScopeItem,
)
from haytham.exporters.spec_transforms import (
    group_stories_by_layer,
    render_gherkin_scenario,
    slugify,
    traits_to_constitution_articles,
)
from haytham.workflow.contracts.execution_contract import ContractStory


class SpecKitExporter(ProjectExporter):
    """Export project data as a Spec Kit directory tree."""

    format_name = "Spec Kit"

    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        """Produce the .specify/ directory tree as {relative_path: content}."""
        tree: dict[str, str] = {}
        tree[".specify/memory/constitution.md"] = self._render_constitution(project)

        for i, scope_item in enumerate(project.scope_items, 1):
            prefix = f".specify/specs/{i:03d}-{slugify(scope_item.name)}"
            caps = [c for c in project.capabilities if c.id in scope_item.capabilities]
            stories = [s for s in project.stories if s.id in scope_item.stories]

            tree[f"{prefix}/spec.md"] = self._render_spec(scope_item, caps, stories)
            tree[f"{prefix}/plan.md"] = self._render_plan(scope_item, project)
            tree[f"{prefix}/tasks.md"] = self._render_tasks(scope_item, stories)

            layer_2 = [s for s in stories if s.layer == 2]
            if layer_2:
                tree[f"{prefix}/data-model.md"] = self._render_data_model(layer_2)

            layer_3 = [s for s in stories if s.layer == 3]
            if layer_3:
                tree[f"{prefix}/contracts/api.md"] = self._render_contracts(layer_3)

        return tree

    # ------------------------------------------------------------------
    # Private renderers
    # ------------------------------------------------------------------

    def _render_constitution(self, project: ExportableProject) -> str:
        """Render constitution.md with system principles, NF capabilities, and versioning."""
        lines: list[str] = []
        lines.append("# Project Constitution")
        lines.append("")

        # System principles from traits
        if project.system_traits:
            lines.append("## System Principles")
            lines.append("")
            articles = traits_to_constitution_articles(project.system_traits)
            if articles:
                lines.append(articles)

        # Non-functional capabilities as quality attribute articles
        if project.non_functional_capabilities:
            lines.append("## Quality Attributes")
            lines.append("")
            for i, cap in enumerate(project.non_functional_capabilities, 1):
                lines.append(f"### Article {i}: {cap.name}")
                lines.append("")
                lines.append(cap.description)
                lines.append("")

        # Versioning footer (required by Spec Kit)
        generated = project.generated_at or "unknown"
        lines.append(
            f"**Version**: 1.0 | **Ratified**: {generated} | **Last Amended**: {generated}"
        )
        lines.append("")

        return "\n".join(lines)

    def _render_spec(
        self,
        scope_item: ExportableScopeItem,
        caps: list[ExportableCapability],
        stories: list[ContractStory],
    ) -> str:
        """Render spec.md with user scenarios, functional requirements, and success criteria."""
        lines: list[str] = []

        lines.append(f"# {scope_item.name}")
        lines.append("")

        # User Scenarios & Testing (layer 3-4 stories with acceptance criteria)
        scenario_stories = [s for s in stories if s.layer in (3, 4)]
        if scenario_stories:
            lines.append("## User Scenarios & Testing")
            lines.append("")
            for idx, story in enumerate(scenario_stories, 1):
                lines.append(f"### User Story {idx} - {story.title}")
                lines.append("")
                if story.summary:
                    lines.append(story.summary)
                    lines.append("")
                for ac in story.acceptance_criteria:
                    lines.append(f"**Scenario: {ac.scenario}**")
                    lines.append("")
                    lines.extend(render_gherkin_scenario(ac, bold_keywords=False))
                    lines.append("")

        # Functional Requirements
        if caps:
            lines.append("## Requirements")
            lines.append("")
            lines.append("### Functional Requirements")
            lines.append("")
            for idx, cap in enumerate(caps, 1):
                fr_id = f"FR-{idx:03d}"
                lines.append(f"- **{fr_id}**: {cap.name} - {cap.description}")
            lines.append("")

        # Success Criteria from acceptance_criteria on stories
        criteria = self._collect_success_criteria(stories)
        if criteria:
            lines.append("## Success Criteria")
            lines.append("")
            lines.append("### Measurable Outcomes")
            lines.append("")
            for idx, criterion in enumerate(criteria, 1):
                sc_id = f"SC-{idx:03d}"
                lines.append(f"- **{sc_id}**: {criterion}")
            lines.append("")

        return "\n".join(lines)

    def _render_plan(
        self,
        scope_item: ExportableScopeItem,
        project: ExportableProject,
    ) -> str:
        """Render plan.md with architecture decisions and build/buy filtered by scope item."""
        lines: list[str] = []
        cap_id_set = set(scope_item.capabilities)

        lines.append(f"# Plan: {scope_item.name}")
        lines.append("")

        # Architecture decisions filtered by serves_capabilities overlap
        relevant_decisions = [
            dec for dec in project.decisions if cap_id_set & set(dec.serves_capabilities)
        ]
        if relevant_decisions:
            lines.append("## Architecture Decisions")
            lines.append("")
            for dec in relevant_decisions:
                lines.append(f"### {dec.id}: {dec.title}")
                lines.append("")
                lines.append(dec.description)
                lines.append("")
                lines.append(f"**Rationale:** {dec.rationale}")
                lines.append("")

        # Build/buy recommendations filtered by capabilities_served overlap
        relevant_services = self._filter_build_buy(project.build_buy, cap_id_set)
        if relevant_services:
            lines.append("## Build/Buy Recommendations")
            lines.append("")
            for svc in relevant_services:
                name = svc.get("name", "Unknown")
                recommendation = svc.get("recommendation", "")
                rationale = svc.get("rationale", "")
                lines.append(f"### {name} ({recommendation})")
                lines.append("")
                if rationale:
                    lines.append(rationale)
                    lines.append("")

        return "\n".join(lines)

    def _render_tasks(
        self,
        scope_item: ExportableScopeItem,
        stories: list[ContractStory],
    ) -> str:
        """Render tasks.md with phased story groupings and sequential task IDs."""
        lines: list[str] = []
        lines.append(f"# Tasks: {scope_item.name}")
        lines.append("")

        by_layer = group_stories_by_layer(stories)

        # Phase 1: Setup (layers 0-1)
        setup = by_layer.get(0, []) + by_layer.get(1, [])
        # Phase 2: Foundational (layer 2)
        foundational = by_layer.get(2, [])
        # Phase 3: User Stories (layers 3-5)
        user_stories: list[ContractStory] = []
        for layer_num in (3, 4, 5):
            user_stories.extend(by_layer.get(layer_num, []))

        task_counter = 0
        for phase_name, phase_stories in [
            ("Phase 1: Setup", setup),
            ("Phase 2: Foundational", foundational),
            ("Phase 3: User Stories", user_stories),
        ]:
            if not phase_stories:
                continue
            lines.append(f"## {phase_name}")
            lines.append("")
            for story in phase_stories:
                task_counter += 1
                tag = "[P]" if not story.depends_on else "[S]"
                lines.append(f"- [ ] T{task_counter:03d} {tag} {story.title} - {story.summary}")
            lines.append("")

        return "\n".join(lines)

    def _render_data_model(self, layer_2_stories: list[ContractStory]) -> str:
        """Render data-model.md from layer 2 stories."""
        lines: list[str] = []
        lines.append("# Data Model")
        lines.append("")

        for story in layer_2_stories:
            lines.append(f"## {story.title}")
            lines.append("")
            if story.content:
                lines.append(story.content)
                lines.append("")
            elif story.summary:
                lines.append(story.summary)
                lines.append("")

        return "\n".join(lines)

    def _render_contracts(self, layer_3_stories: list[ContractStory]) -> str:
        """Render contracts/api.md from layer 3 stories."""
        lines: list[str] = []
        lines.append("# API Contracts")
        lines.append("")

        for story in layer_3_stories:
            lines.append(f"## {story.title}")
            lines.append("")
            if story.content:
                lines.append(story.content)
                lines.append("")
            elif story.summary:
                lines.append(story.summary)
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_success_criteria(stories: list[ContractStory]) -> list[str]:
        """Collect unique success criteria text from story acceptance_criteria."""
        criteria: list[str] = []
        for story in stories:
            for ac in story.acceptance_criteria:
                criteria.append(ac.scenario)
        return criteria

    @staticmethod
    def _filter_build_buy(
        build_buy: dict | None,
        cap_id_set: set[str],
    ) -> list[dict]:
        """Filter build/buy recommended_stack by capabilities_served overlap."""
        if not build_buy:
            return []
        stack = build_buy.get("recommended_stack", [])
        return [svc for svc in stack if cap_id_set & set(svc.get("capabilities_served", []))]
