"""AI-ready project scaffold exporter.

Produces a project directory with context files for AI coding tools,
bundled with OpenSpec and Spec Kit exports.

File format choices follow each tool's official best practices:
- CLAUDE.md: <200 lines, @path imports, specific verifiable rules
  (https://code.claude.com/docs/en/memory)
- AGENTS.md: Universal format for 20+ AI tools, standard sections
  (https://agents.md)
- copilot-instructions.md: Short imperative directives, <2 pages
  (https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- .cursorrules: Concise actionable rules (legacy Cursor format)

Tree layout:

    CLAUDE.md
    AGENTS.md
    .cursorrules
    .github/
        copilot-instructions.md
    README.md
    openspec/...              (delegated to OpenSpecExporter)
    .specify/...              (delegated to SpecKitExporter)
"""

from haytham.exporters.openspec_exporter import OpenSpecExporter
from haytham.exporters.project_exporter_base import ProjectExporter
from haytham.exporters.project_model import ExportableProject
from haytham.exporters.speckit_exporter import SpecKitExporter


class ScaffoldExporter(ProjectExporter):
    """Export project data as an AI-ready project scaffold."""

    format_name = "AI Scaffold"

    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        """Produce the scaffold directory tree as {relative_path: content}."""
        tree: dict[str, str] = {}

        # AI coding tool context files
        tree["CLAUDE.md"] = self._render_claude_md(project)
        tree["AGENTS.md"] = self._render_agents_md(project)
        tree[".cursorrules"] = self._render_cursorrules(project)
        tree[".github/copilot-instructions.md"] = self._render_copilot_instructions(project)
        tree["README.md"] = self._render_readme(project)

        # Delegate to existing exporters for spec subtrees
        tree.update(OpenSpecExporter().export_tree(project))
        tree.update(SpecKitExporter().export_tree(project))

        return tree

    # ------------------------------------------------------------------
    # CLAUDE.md -- rich context, <200 lines, @imports for spec references
    # ------------------------------------------------------------------

    def _render_claude_md(self, project: ExportableProject) -> str:
        """Render CLAUDE.md following Claude Code best practices.

        Best practices applied:
        - Under 200 lines for optimal adherence
        - Use @path imports to reference spec files instead of inlining
        - Specific, verifiable instructions (not vague guidance)
        - Markdown headers + bullets for scannable structure
        - Omit empty sections entirely
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        lines.append(f"# {name}")
        lines.append("")

        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        # Hard constraints as verifiable rules
        if project.explicit_constraints:
            lines.append("## Hard Constraints")
            lines.append("")
            for constraint in project.explicit_constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        # Explicit DO NOT list from concept anchor non-goals
        if project.non_goals:
            lines.append("## What This Project Is NOT")
            lines.append("")
            lines.append("DO NOT build or suggest any of the following:")
            lines.append("")
            for non_goal in project.non_goals:
                lines.append(f"- {non_goal}")
            lines.append("")

        # Identity risks (genericization warnings from ADR-022)
        if project.identity_risks:
            lines.append("## Identity Risks")
            lines.append("")
            lines.append("These features are distinctive. Do NOT genericize them:")
            lines.append("")
            for risk in project.identity_risks:
                lines.append(f"- {risk}")
            lines.append("")

        # System architecture from traits
        if project.system_traits:
            lines.append("## System Architecture")
            lines.append("")
            for key, value in project.system_traits.items():
                label = key.replace("_", " ").title()
                lines.append(f"- **{label}:** {value}")
            lines.append("")

        # Tech stack decisions with rationale
        if project.decisions:
            lines.append("## Tech Stack")
            lines.append("")
            for dec in project.decisions:
                rec = f" ({dec.implements})" if dec.implements else ""
                lines.append(f"### {dec.id}: {dec.title}{rec}")
                lines.append("")
                lines.append(dec.description)
                if dec.rationale:
                    lines.append(f"**Rationale:** {dec.rationale}")
                lines.append("")

        # Capabilities as compact table
        if project.capabilities:
            lines.append("## Capabilities")
            lines.append("")
            lines.append("| ID | Name | Scope Item |")
            lines.append("|---|---|---|")
            for cap in project.capabilities:
                scope = cap.serves_scope_item or "-"
                lines.append(f"| {cap.id} | {cap.name} | {scope} |")
            lines.append("")

        # Non-functional requirements
        if project.non_functional_capabilities:
            lines.append("## Non-Functional Requirements")
            lines.append("")
            for cap in project.non_functional_capabilities:
                lines.append(f"- **{cap.name}:** {cap.description}")
            lines.append("")

        # @imports for spec files (Claude Code best practice)
        lines.append("## Detailed Specifications")
        lines.append("")
        lines.append("@openspec/project.md")
        lines.append("")
        lines.append(
            "For full feature specifications, see `openspec/specs/` and `.specify/specs/`."
        )
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # AGENTS.md -- universal format for 20+ AI agents
    # ------------------------------------------------------------------

    def _render_agents_md(self, project: ExportableProject) -> str:
        """Render AGENTS.md following the agents.md standard.

        Standard sections: Project Overview, Build & Test, Code Style,
        Testing, Project Structure, Security. Works with Codex, Cursor,
        Copilot, Aider, and 20+ other AI coding tools.
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        # Project Overview (required by agents.md)
        lines.append(f"# {name}")
        lines.append("")
        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        if project.non_goals:
            lines.append("**This project is NOT:**")
            for non_goal in project.non_goals:
                lines.append(f"- {non_goal}")
            lines.append("")

        # Tech Stack (agents.md recommended section)
        if project.decisions or project.system_traits:
            lines.append("## Tech Stack")
            lines.append("")
            if project.system_traits:
                for key, value in project.system_traits.items():
                    label = key.replace("_", " ").title()
                    lines.append(f"- **{label}:** {value}")
                lines.append("")
            if project.decisions:
                for dec in project.decisions:
                    lines.append(f"- **{dec.title}:** {dec.description}")
                lines.append("")

        # Build & Test Commands (agents.md recommended section)
        lines.append("## Build & Test Commands")
        lines.append("")
        lines.append("<!-- TODO: Add build and test commands after project setup -->")
        lines.append("")

        # Code Style & Guidelines (agents.md recommended section)
        lines.append("## Code Style & Guidelines")
        lines.append("")
        if project.explicit_constraints:
            for constraint in project.explicit_constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        # Quality Requirements
        if project.non_functional_capabilities:
            lines.append("## Quality Requirements")
            lines.append("")
            for cap in project.non_functional_capabilities:
                lines.append(f"- **{cap.name}:** {cap.description}")
            lines.append("")

        # Project Structure (agents.md recommended section)
        lines.append("## Project Structure")
        lines.append("")
        lines.append("- `openspec/` - Feature specifications with acceptance criteria")
        lines.append("- `openspec/config.yaml` - Project metadata and system traits")
        lines.append("- `openspec/specs/` - Per-domain requirement specs")
        lines.append("- `.specify/` - Implementation tasks organized by domain")
        lines.append("- `.specify/memory/constitution.md` - System principles")
        lines.append("- `.specify/specs/` - Per-feature spec, plan, and tasks")
        lines.append("")

        # Footer
        generated = project.generated_at or "unknown"
        lines.append("---")
        lines.append("")
        lines.append(f"Generated by [Haytham](https://github.com/arslan70/haytham) on {generated}")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # .github/copilot-instructions.md -- imperative, <2 pages
    # ------------------------------------------------------------------

    def _render_copilot_instructions(self, project: ExportableProject) -> str:
        """Render copilot-instructions.md following GitHub's 5 tips.

        Tips applied:
        1. Project overview (elevator pitch)
        2. Tech stack (frameworks and tools)
        3. Coding guidelines (constraints, non-goals)
        4. Project structure (folder map)
        5. Available resources (spec file pointers)
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        # Tip 1: Project overview
        lines.append(f"# {name}")
        lines.append("")
        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        # Tip 2: Tech stack
        if project.decisions:
            lines.append("## Tech Stack")
            lines.append("")
            for dec in project.decisions:
                target = (
                    ", ".join(dec.serves_capabilities)
                    if dec.serves_capabilities
                    else "this project"
                )
                lines.append(f"- Use {dec.title} for {target}.")
            lines.append("")

        # Tip 3: Coding guidelines
        guidelines: list[str] = []
        if project.explicit_constraints:
            guidelines.extend(project.explicit_constraints)
        if project.non_goals:
            for ng in project.non_goals:
                guidelines.append(f"Do not build: {ng}")
        if project.system_traits:
            for key, value in project.system_traits.items():
                label = key.replace("_", " ")
                guidelines.append(f"Use {value} for {label}")

        if guidelines:
            lines.append("## Guidelines")
            lines.append("")
            for g in guidelines:
                lines.append(f"- {g}")
            lines.append("")

        # Tip 4: Project structure
        lines.append("## Project Structure")
        lines.append("")
        lines.append("- `openspec/` - Feature specifications with acceptance criteria")
        lines.append("- `.specify/` - Implementation tasks organized by domain")
        lines.append("")

        # Tip 5: Available resources
        lines.append("## Resources")
        lines.append("")
        lines.append("- `openspec/project.md` - Architecture decisions and tech stack")
        lines.append("- `openspec/specs/` - Per-domain requirement specifications")
        lines.append("- `.specify/specs/` - Per-feature implementation plans and tasks")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # .cursorrules -- concise actionable rules (legacy Cursor format)
    # ------------------------------------------------------------------

    def _render_cursorrules(self, project: ExportableProject) -> str:
        """Render .cursorrules with concise, actionable rules.

        Best practices: specific over vague, every word counts,
        keep it under 80 lines.
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        lines.append(f"# {name}")
        lines.append("")

        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        # Non-goals as DO NOT rules
        if project.non_goals:
            lines.append("## DO NOT")
            lines.append("")
            for non_goal in project.non_goals:
                lines.append(f"- {non_goal}")
            lines.append("")

        # Tech stack as rules
        if project.decisions:
            lines.append("## Tech Stack (do not suggest alternatives)")
            lines.append("")
            for dec in project.decisions:
                lines.append(f"- **{dec.title}**: {dec.description}")
            lines.append("")

        # System constraints
        if project.system_traits:
            lines.append("## System Constraints")
            lines.append("")
            for key, value in project.system_traits.items():
                label = key.replace("_", " ").title()
                lines.append(f"- {label}: {value}")
            lines.append("")

        # Reference
        lines.append("## Reference")
        lines.append("")
        lines.append("- `openspec/` - Feature specifications with acceptance criteria")
        lines.append("- `.specify/` - Implementation tasks organized by domain")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # README.md -- human-readable overview
    # ------------------------------------------------------------------

    def _render_readme(self, project: ExportableProject) -> str:
        """Render README.md with human-readable project overview."""
        lines: list[str] = []
        name = project.project_name or "Project"

        lines.append(f"# {name}")
        lines.append("")
        if project.idea_summary:
            lines.append(project.idea_summary)
            lines.append("")

        if project.appetite:
            lines.append(f"**Appetite:** {project.appetite}")
            lines.append("")

        # Features
        if project.capabilities:
            lines.append("## Features")
            lines.append("")
            for cap in project.capabilities:
                lines.append(f"- **{cap.name}**: {cap.description}")
            lines.append("")

        # Tech stack
        if project.decisions:
            lines.append("## Tech Stack")
            lines.append("")
            for dec in project.decisions:
                lines.append(f"- **{dec.title}**: {dec.description}")
            lines.append("")

        # Generated by
        generated = project.generated_at or "unknown"
        lines.append("---")
        lines.append("")
        lines.append(f"Generated by [Haytham](https://github.com/arslan70/haytham) on {generated}")
        lines.append("")

        return "\n".join(lines)
