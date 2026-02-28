"""OpenSpec directory tree exporter.

Produces the openspec/ structure consumed by AI coding agents via the
@fission-ai/openspec toolchain. The tree layout:

    openspec/
    +-- config.yaml
    +-- project.md
    +-- specs/
        +-- <domain-slug>/
        |   +-- spec.md
        +-- cross-cutting/
            +-- spec.md
"""

import yaml

from haytham.exporters.project_exporter_base import ProjectExporter
from haytham.exporters.project_model import (
    ExportableCapability,
    ExportableProject,
    ExportableScopeItem,
)
from haytham.exporters.spec_transforms import (
    capability_to_shall_statement,
    render_gherkin_scenario,
    slugify,
)
from haytham.workflow.contracts.execution_contract import ContractStory


class OpenSpecExporter(ProjectExporter):
    """Export project data as an OpenSpec directory tree."""

    format_name = "OpenSpec"

    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        """Produce the openspec/ directory tree as {relative_path: content}."""
        tree: dict[str, str] = {}
        tree["openspec/config.yaml"] = self._render_config(project)
        tree["openspec/project.md"] = self._render_project(project)

        for scope_item in project.scope_items:
            if scope_item.name == "Infrastructure":
                continue
            domain_slug = slugify(scope_item.name)
            caps = [c for c in project.capabilities if c.id in scope_item.capabilities]
            stories = [s for s in project.stories if s.id in scope_item.stories]
            tree[f"openspec/specs/{domain_slug}/spec.md"] = self._render_spec(
                scope_item, caps, stories
            )

        if project.non_functional_capabilities:
            tree["openspec/specs/cross-cutting/spec.md"] = self._render_non_functional_spec(
                project.non_functional_capabilities
            )

        return tree

    # ------------------------------------------------------------------
    # Private renderers
    # ------------------------------------------------------------------

    def _render_config(self, project: ExportableProject) -> str:
        """Render config.yaml with project metadata and system traits."""
        config: dict = {
            "name": project.project_name or project.idea_summary,
            "version": "1.0.0",
        }
        if project.idea_summary:
            config["description"] = project.idea_summary
        if project.appetite:
            config["appetite"] = project.appetite
        if project.generated_at:
            config["generated_at"] = project.generated_at
        if project.system_traits:
            config["traits"] = project.system_traits
        return yaml.safe_dump(config, default_flow_style=False, sort_keys=False)

    def _render_project(self, project: ExportableProject) -> str:
        """Render project.md with tech stack and architecture decisions."""
        lines: list[str] = []
        lines.append("# Project Overview")
        lines.append("")
        lines.append(project.idea_summary)
        lines.append("")

        if project.system_traits:
            lines.append("## Tech Stack")
            lines.append("")
            for key, value in project.system_traits.items():
                label = key.replace("_", " ").title()
                lines.append(f"- **{label}:** {value}")
            lines.append("")

        if project.decisions:
            lines.append("## Architecture Decisions")
            lines.append("")
            for decision in project.decisions:
                lines.append(f"### {decision.id}: {decision.title}")
                lines.append("")
                lines.append(decision.description)
                lines.append("")
                lines.append(f"**Rationale:** {decision.rationale}")
                lines.append("")

        return "\n".join(lines)

    def _render_spec(
        self,
        scope_item: ExportableScopeItem,
        caps: list[ExportableCapability],
        stories: list[ContractStory],
    ) -> str:
        """Render spec.md for a single scope item (domain)."""
        lines: list[str] = []

        lines.append(f"# {scope_item.name} Specification")
        lines.append("")
        lines.append("## Purpose")
        lines.append("")
        lines.append(scope_item.description or f"Requirements for {scope_item.name}.")
        lines.append("")

        # Build a lookup from capability ID to linked stories
        cap_stories: dict[str, list[ContractStory]] = {}
        for cap in caps:
            cap_stories[cap.id] = [s for s in stories if cap.id in s.implements]

        for cap in caps:
            shall = capability_to_shall_statement(cap)
            lines.append(f"### Requirement: {cap.name}")
            lines.append("")
            lines.append(shall)
            lines.append("")

            linked = cap_stories.get(cap.id, [])
            has_scenarios = False
            seen_scenarios: set[tuple[str, str, str, str]] = set()

            # Try to render scenarios from linked stories' acceptance criteria
            for story in linked:
                for ac in story.acceptance_criteria:
                    key = (ac.scenario, ac.given, ac.when, ac.then)
                    if key in seen_scenarios:
                        continue
                    seen_scenarios.add(key)
                    has_scenarios = True
                    lines.append(f"#### Scenario: {ac.scenario}")
                    lines.append("")
                    lines.extend(render_gherkin_scenario(ac, bold_keywords=True))
                    lines.append("")

            # Fallback: use capability's own acceptance_criteria
            if not has_scenarios and cap.acceptance_criteria:
                for criterion in cap.acceptance_criteria:
                    lines.append(f"#### Scenario: {criterion}")
                    lines.append("")
                    lines.append("- **Given** the system is operational")
                    lines.append("- **When** the condition is evaluated")
                    lines.append(f"- **Then** {criterion}")
                    lines.append("")

        return "\n".join(lines)

    def _render_non_functional_spec(
        self,
        nf_capabilities: list[ExportableCapability],
    ) -> str:
        """Render cross-cutting/spec.md for non-functional capabilities.

        Non-functional requirements are rendered as SHALL statements only.
        Unlike functional specs, they have no story-backed Gherkin scenarios
        to draw from, so omitting placeholder scenarios avoids noise.
        """
        lines: list[str] = []

        lines.append("# Cross-Cutting Requirements")
        lines.append("")
        lines.append("## Purpose")
        lines.append("")
        lines.append("Non-functional requirements that apply across all domains.")
        lines.append("")

        for cap in nf_capabilities:
            shall = capability_to_shall_statement(cap)
            lines.append(f"### {cap.name}")
            lines.append("")
            lines.append(shall)
            lines.append("")

        return "\n".join(lines)
