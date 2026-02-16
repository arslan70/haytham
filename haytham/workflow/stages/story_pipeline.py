"""Story-pipeline phase orchestration (STORIES).

Functions used by story-generation, story-validation, dependency-ordering
stage configs.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from burr.core import State

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Story generation
# ---------------------------------------------------------------------------


def run_story_generation(state: State) -> tuple[str, str]:
    """Generate implementation-ready user stories using structured output.

    Uses Strands structured_output_model to produce validated JSON matching
    StoryGenerationHybridOutput. Returns markdown for display/session and
    saves stories.json for structured consumption by downstream stages.

    Creates layered stories that an AI coding agent can execute sequentially:
    - Layer 0: Project foundation (init, types, database, schema, seed data)
    - Layer 1: Authentication (signup, login, middleware, layout)
    - Layer 2: Third-party integrations
    - Layer 3: API endpoints / core functionality
    - Layer 4: Feature UI
    - Layer 5: Real-time features
    """
    from haytham.agents.worker_story_generator.story_swarm import run_story_swarm

    # Gather all context
    system_goal = state.get("system_goal", "")
    mvp_scope = state.get("mvp_scope", "")
    capability_model = state.get("capability_model", "")
    architecture_decisions = state.get("architecture_decisions", "")
    build_buy_analysis = state.get("build_buy_analysis", "")

    if not capability_model:
        return "Error: No capability model found", "failed"

    try:
        logger.info("Generating specification stories...")

        # Run the swarm - returns (markdown, stories_dicts)
        stories_markdown, stories_dicts = run_story_swarm(
            mvp_scope=mvp_scope,
            capability_model=capability_model,
            architecture_decisions=architecture_decisions,
            build_buy_analysis=build_buy_analysis,
            system_goal=system_goal,
        )

        if not stories_markdown or not stories_markdown.strip():
            logger.error("Story swarm produced no output")
            return "Error: Story generation swarm produced no output.", "failed"

        # Save stories.json alongside the markdown for downstream consumers
        if stories_dicts:
            session_manager = state.get("session_manager")
            if session_manager:
                stories_json_path = (
                    Path(session_manager.session_dir) / "story-generation" / "stories.json"
                )
                stories_json_path.parent.mkdir(parents=True, exist_ok=True)
                stories_json_path.write_text(json.dumps(stories_dicts, indent=2))
                logger.info(f"Saved {len(stories_dicts)} stories to {stories_json_path}")

        logger.info("Story generation completed successfully")

        # Return JSON for Burr state; executor renders markdown for disk via output_model
        if stories_dicts:
            return json.dumps({"stories": stories_dicts}), "completed"
        return stories_markdown, "completed"

    except Exception as e:
        logger.error(f"Story generation swarm failed: {e}", exc_info=True)
        return f"Error generating stories: {str(e)}", "failed"


# ---------------------------------------------------------------------------
# Story validation
# ---------------------------------------------------------------------------


def run_story_validation(state: State) -> tuple[str, str]:
    """Validate generated stories for completeness and quality.

    Validates:
    - Layer completeness (0: foundation, 1: auth, 2+: features)
    - Capability coverage (all CAP-F-* and CAP-NF-* have stories)
    - Decision coverage (all DEC-* are implemented)
    - Dependency validity (no circular dependencies)
    - Technical specification quality
    """
    story_generation = state.get("story_generation", "")
    capability_model = state.get("capability_model", "")
    architecture_decisions = state.get("architecture_decisions", "")

    if not story_generation:
        return "Error: No stories found to validate", "failed"

    # Parse capabilities
    from haytham.agents.output_utils import extract_json_from_text

    functional_caps = []
    non_functional_caps = []
    cap_data = extract_json_from_text(capability_model)
    if cap_data:
        functional_caps = cap_data.get("capabilities", {}).get("functional", [])
        non_functional_caps = cap_data.get("capabilities", {}).get("non_functional", [])

    cap_f_ids = [c.get("id") for c in functional_caps if c.get("id")]
    cap_nf_ids = [c.get("id") for c in non_functional_caps if c.get("id")]
    all_cap_ids = cap_f_ids + cap_nf_ids

    # Extract decision IDs from architecture decisions
    dec_pattern = r"DEC-[A-Z]+-\d+"
    decision_ids = list(set(re.findall(dec_pattern, architecture_decisions)))

    # Try to parse story_generation as JSON first (output_model stores JSON in state)
    stories_parsed: list[dict] | None = None
    try:
        sg_data = json.loads(story_generation)
        if isinstance(sg_data, dict) and "stories" in sg_data:
            stories_parsed = sg_data["stories"]
    except (json.JSONDecodeError, TypeError):
        pass

    if stories_parsed is not None:
        # Structured path: extract validation data from parsed stories
        layer_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        covered_caps = []
        uncovered_caps = list(all_cap_ids)
        covered_decs = []
        uncovered_decs = list(decision_ids)

        for story in stories_parsed:
            layer = story.get("layer", 4)
            if layer in layer_counts:
                layer_counts[layer] += 1

            # Check capability coverage via implements field
            for cap_id in story.get("implements", []):
                if cap_id in uncovered_caps:
                    uncovered_caps.remove(cap_id)
                    covered_caps.append(cap_id)

            # Check decision coverage via implements field + content
            story_text = json.dumps(story)
            for dec_id in list(uncovered_decs):
                if dec_id in story_text:
                    uncovered_decs.remove(dec_id)
                    covered_decs.append(dec_id)

        has_layer_0 = layer_counts.get(0, 0) > 0
        has_layer_1 = layer_counts.get(1, 0) > 0
        total_stories = len(stories_parsed)
    else:
        # Fallback: regex-based validation for markdown (backward compat)
        # Check layer completeness
        has_layer_0 = any(
            x in story_generation.lower()
            for x in [
                "layer 0",
                "layer: 0",
                "project foundation",
                "initialize project",
                "database schema",
                "supabase client",
            ]
        )
        has_layer_1 = any(
            x in story_generation.lower()
            for x in [
                "layer 1",
                "layer: 1",
                "authentication",
                "user registration",
                "user login",
                "auth middleware",
            ]
        )

        # Check capability coverage
        covered_caps = []
        uncovered_caps = []
        for cap_id in all_cap_ids:
            if cap_id and cap_id in story_generation:
                covered_caps.append(cap_id)
            else:
                uncovered_caps.append(cap_id)

        # Check decision coverage
        covered_decs = []
        uncovered_decs = []
        for dec_id in decision_ids:
            if dec_id in story_generation:
                covered_decs.append(dec_id)
            else:
                uncovered_decs.append(dec_id)

        # Count stories by layer (look for layer indicators)
        layer_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        layer_patterns = [
            (0, r"Layer 0|layer: 0|layer\":?\s*0"),
            (1, r"Layer 1|layer: 1|layer\":?\s*1"),
            (2, r"Layer 2|layer: 2|layer\":?\s*2"),
            (3, r"Layer 3|layer: 3|layer\":?\s*3"),
            (4, r"Layer 4|layer: 4|layer\":?\s*4"),
            (5, r"Layer 5|layer: 5|layer\":?\s*5"),
        ]
        for layer, pattern in layer_patterns:
            layer_counts[layer] = len(re.findall(pattern, story_generation, re.IGNORECASE))

        # Total story count
        story_pattern = r"STORY-\d+|### STORY-|## \d+\.|Story \d+:"
        total_stories = len(re.findall(story_pattern, story_generation, re.IGNORECASE))

    # Build validation report
    output_md = "# Story Validation Report\n\n"

    # Layer completeness
    output_md += "## Layer Completeness\n\n"
    layer_names = {
        0: "Project Foundation",
        1: "Authentication",
        2: "Third-Party Integrations",
        3: "API Endpoints",
        4: "Feature UI",
        5: "Non-Functional Requirements",
    }
    for layer, name in layer_names.items():
        count = layer_counts.get(layer, 0)
        if layer == 0:
            status = "pass" if has_layer_0 else "MISSING"
        elif layer == 1:
            status = "pass" if has_layer_1 else "MISSING"
        else:
            status = "pass" if count > 0 else "warning"
        output_md += f"- Layer {layer} ({name}): {status} ({count} stories)\n"
    output_md += "\n"

    # Capability coverage
    cap_coverage = (len(covered_caps) / len(all_cap_ids) * 100) if all_cap_ids else 100
    output_md += "## Capability Coverage\n\n"
    output_md += f"- **Total Capabilities:** {len(all_cap_ids)} ({len(cap_f_ids)} functional, {len(cap_nf_ids)} non-functional)\n"
    output_md += f"- **Covered by Stories:** {len(covered_caps)}\n"
    output_md += f"- **Coverage:** {cap_coverage:.0f}%\n\n"

    if covered_caps:
        output_md += "**Covered:**\n"
        for cap_id in covered_caps:
            output_md += f"- PASS {cap_id}\n"
        output_md += "\n"

    if uncovered_caps:
        output_md += "**Uncovered (Need Stories):**\n"
        for cap_id in uncovered_caps:
            output_md += f"- FAIL {cap_id}\n"
        output_md += "\n"

    # Decision coverage
    if decision_ids:
        dec_coverage = (len(covered_decs) / len(decision_ids) * 100) if decision_ids else 100
        output_md += "## Decision Coverage\n\n"
        output_md += f"- **Architecture Decisions:** {len(decision_ids)}\n"
        output_md += f"- **Implemented by Stories:** {len(covered_decs)}\n"
        output_md += f"- **Coverage:** {dec_coverage:.0f}%\n\n"

        if uncovered_decs:
            output_md += "**Uncovered Decisions:**\n"
            for dec_id in uncovered_decs:
                output_md += f"- FAIL {dec_id}\n"
            output_md += "\n"

    # Overall assessment
    output_md += "## Overall Assessment\n\n"

    issues = []
    if not has_layer_0:
        issues.append("Missing Layer 0 (Project Foundation) stories")
    if not has_layer_1:
        issues.append("Missing Layer 1 (Authentication) stories")
    if uncovered_caps:
        issues.append(f"{len(uncovered_caps)} capabilities not covered")
    if uncovered_decs:
        issues.append(f"{len(uncovered_decs)} architecture decisions not implemented")
    if total_stories < 15:
        issues.append(f"Only {total_stories} stories - typical MVP needs 20-35")

    if not issues:
        output_md += (
            "### PASSED\n\nAll validation checks passed. Stories are ready for implementation.\n"
        )
    elif len(issues) <= 2:
        output_md += "### PARTIAL PASS\n\nMost checks passed with minor issues:\n"
        for issue in issues:
            output_md += f"- {issue}\n"
    else:
        output_md += "### NEEDS IMPROVEMENT\n\nSignificant gaps found:\n"
        for issue in issues:
            output_md += f"- {issue}\n"

    output_md += f"\n**Total Stories:** {total_stories}\n"

    return output_md, "completed"


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------


def parse_stories_from_markdown(markdown: str) -> list[dict]:
    """Parse stories from YAML frontmatter markdown format.

    Handles the story generation output format where each story has:
    - YAML frontmatter between --- markers (id, title, layer, implements, depends_on)
    - Body content after the closing --- (description, acceptance criteria, files, verification)
    - Optional code fence wrapping (``` blocks around stories)

    Returns:
        List of story dicts with keys: id, title, layer, depends_on, implements, content
    """
    stories = []

    # Strip code fence wrappers - some stories are wrapped in ``` blocks
    # Remove standalone ``` lines (not code blocks within story content)
    cleaned = re.sub(r"^```\s*$", "", markdown, flags=re.MULTILINE)

    # Split on YAML frontmatter opening markers.
    # Each story starts with --- followed by id: STORY-NNN
    # We split just before each --- that precedes an id: line
    parts = re.split(r"(?=^---\s*\nid:\s*STORY-)", cleaned, flags=re.MULTILINE)

    for part in parts:
        part = part.strip()
        if not part or not part.startswith("---"):
            continue

        # Split frontmatter from body at the closing ---
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*$(.*)", part, re.DOTALL | re.MULTILINE)
        if not fm_match:
            continue

        frontmatter_text = fm_match.group(1)
        body = fm_match.group(2).strip()

        # Remove trailing --- that acts as a story separator (not content)
        body = re.sub(r"\n---\s*$", "", body).strip()

        # Parse frontmatter fields
        id_match = re.search(r"^id:\s*(.+)$", frontmatter_text, re.MULTILINE)
        title_match = re.search(r"^title:\s*(.+)$", frontmatter_text, re.MULTILINE)
        layer_match = re.search(r"^layer:\s*(\d+)", frontmatter_text, re.MULTILINE)
        impl_match = re.search(r"^implements:\s*\[([^\]]*)\]", frontmatter_text, re.MULTILINE)
        deps_match = re.search(r"^depends_on:\s*\[([^\]]*)\]", frontmatter_text, re.MULTILINE)

        story_id = id_match.group(1).strip() if id_match else None
        if not story_id:
            continue

        title = title_match.group(1).strip() if title_match else "Untitled"
        layer = int(layer_match.group(1)) if layer_match else 4

        depends_on = []
        if deps_match and deps_match.group(1).strip():
            depends_on = [d.strip().strip("'\"") for d in deps_match.group(1).split(",")]

        implements = []
        if impl_match and impl_match.group(1).strip():
            implements = [i.strip().strip("'\"") for i in impl_match.group(1).split(",")]

        stories.append(
            {
                "id": story_id,
                "title": title,
                "layer": layer,
                "depends_on": depends_on,
                "implements": implements,
                "content": body,
            }
        )

    return stories


# ---------------------------------------------------------------------------
# Dependency ordering
# ---------------------------------------------------------------------------


def run_dependency_ordering(state: State) -> tuple[str, str]:
    """Create implementation roadmap with stories ordered by dependencies.

    Orders stories by:
    1. Layer (0 -> 5)
    2. Dependencies (topological sort within each layer)
    3. Priority (CAP-F before CAP-NF)
    """
    story_generation = state.get("story_generation", "")

    if not story_generation:
        return "Error: No stories found to order", "failed"

    stories = []

    # Try to parse from Burr state JSON first (output_model stores JSON)
    try:
        sg_data = json.loads(story_generation)
        if isinstance(sg_data, dict) and "stories" in sg_data:
            stories = sg_data["stories"]
            logger.info(f"Loaded {len(stories)} stories from Burr state JSON")
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: Try to read from stories.json on disk
    if not stories:
        session_manager = state.get("session_manager")
        if session_manager:
            stories_json_path = (
                Path(session_manager.session_dir) / "story-generation" / "stories.json"
            )
            if stories_json_path.exists():
                try:
                    stories = json.loads(stories_json_path.read_text())
                    logger.info(f"Loaded {len(stories)} stories from stories.json")
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to read stories.json: {e}")

    # Fallback: parse from markdown
    if not stories:
        stories = parse_stories_from_markdown(story_generation)

    # If no structured stories found, fall back to simple extraction
    if not stories:
        simple_pattern = r"## Story (\d+):\s*([^\n]+)"
        simple_matches = re.findall(simple_pattern, story_generation)
        for num, title in simple_matches:
            stories.append(
                {
                    "id": f"STORY-{int(num):03d}",
                    "title": title,
                    "layer": 4,  # Default to feature layer
                    "depends_on": [],
                    "implements": [],
                    "content": "",
                }
            )

    # Group stories by layer
    stories_by_layer = {}
    for story in stories:
        layer = story.get("layer", 4)
        if layer not in stories_by_layer:
            stories_by_layer[layer] = []
        stories_by_layer[layer].append(story)

    # Build roadmap output
    output_md = "# Implementation Roadmap\n\n"
    output_md += "Stories ordered by layer and dependencies for sequential implementation.\n\n"
    output_md += f"**Total Stories:** {len(stories)}\n\n"
    output_md += "---\n\n"

    layer_names = {
        0: "Project Foundation",
        1: "Authentication",
        2: "Third-Party Integrations",
        3: "API Endpoints",
        4: "Feature UI",
        5: "Non-Functional Requirements",
    }

    layer_descriptions = {
        0: "Set up the project structure, dependencies, and database schema.",
        1: "Implement user authentication flows.",
        2: "Configure third-party service integrations.",
        3: "Create API endpoints for data operations.",
        4: "Build user-facing pages and components.",
        5: "Add data validation, notifications, and polish.",
    }

    story_number = 1
    for layer in sorted(stories_by_layer.keys()):
        layer_stories = stories_by_layer[layer]
        layer_name = layer_names.get(layer, f"Layer {layer}")
        layer_desc = layer_descriptions.get(layer, "")

        output_md += f"## Phase {layer}: {layer_name}\n\n"
        if layer_desc:
            output_md += f"*{layer_desc}*\n\n"

        # Sort stories within layer by dependencies (simple topological sort)
        ordered = []
        remaining = layer_stories.copy()
        completed_ids = set()

        # Add stories from previous layers as completed
        for prev_layer in range(layer):
            for s in stories_by_layer.get(prev_layer, []):
                completed_ids.add(s["id"])

        max_iterations = len(remaining) + 1
        iteration = 0
        while remaining and iteration < max_iterations:
            iteration += 1
            for story in remaining[:]:
                deps = story.get("depends_on", [])
                # Check if all dependencies are satisfied
                deps_satisfied = all(
                    d in completed_ids or d not in [s["id"] for s in stories] for d in deps
                )
                if deps_satisfied or not deps:
                    ordered.append(story)
                    remaining.remove(story)
                    completed_ids.add(story["id"])

        # Add any remaining (circular deps or missing deps)
        ordered.extend(remaining)

        for story in ordered:
            story_id = story.get("id", f"STORY-{story_number:03d}")
            title = story.get("title", "Untitled")
            implements = story.get("implements", [])
            depends_on = story.get("depends_on", [])

            output_md += f"### {story_number}. {story_id}: {title}\n\n"

            if implements:
                output_md += f"- **Implements:** {', '.join(implements)}\n"
            if depends_on:
                output_md += f"- **Depends on:** {', '.join(depends_on)}\n"

            output_md += "- [ ] Ready for implementation\n\n"
            story_number += 1

        output_md += "---\n\n"

    # Summary
    output_md += "## Implementation Summary\n\n"
    output_md += "| Layer | Name | Stories |\n"
    output_md += "|-------|------|--------|\n"
    for layer in sorted(stories_by_layer.keys()):
        name = layer_names.get(layer, f"Layer {layer}")
        count = len(stories_by_layer[layer])
        output_md += f"| {layer} | {name} | {count} |\n"

    output_md += f"\n**Total Implementation Steps:** {len(stories)}\n"

    return output_md, "completed"


# ---------------------------------------------------------------------------
# Backlog draft creation
# ---------------------------------------------------------------------------


def create_backlog_drafts_from_stories(
    stories: list,
    project_dir: str | None = None,
) -> dict:
    """Create Backlog.md drafts from generated stories.

    Args:
        stories: List of Story objects or dicts
        project_dir: Project directory (defaults to current working directory)

    Returns:
        Dict with created_count, failed_count, and draft_ids
    """
    from haytham.backlog.cli import BacklogCLI

    if project_dir is None:
        project_dir = Path.cwd()

    cli = BacklogCLI(project_dir)

    # Ensure backlog is initialized
    if not cli.is_initialized():
        logger.warning("Backlog not initialized, attempting to initialize...")
        cli.init("Haytham Generated MVP")

    created_count = 0
    failed_count = 0
    draft_ids = []

    for story in stories:
        # Handle both Story objects and dicts
        if hasattr(story, "model_dump"):
            story_dict = story.model_dump()
        else:
            story_dict = story

        story_id = story_dict.get("id", "")
        title = story_dict.get("title", "Untitled Story")
        layer = story_dict.get("layer", 0)
        depends_on = story_dict.get("depends_on", [])
        implements = story_dict.get("implements", [])

        # Check if this is markdown-based (has 'content' field) or structured
        if "content" in story_dict:
            # New markdown-based format from swarm
            full_description = story_dict["content"]

            # Extract acceptance criteria from content if present
            acceptance_criteria = []
            ac_match = re.search(
                r"## Acceptance Criteria\n(.*?)(?=\n## |\n---|\Z)", full_description, re.DOTALL
            )
            if ac_match:
                ac_lines = ac_match.group(1).strip().split("\n")
                for line in ac_lines:
                    line = line.strip()
                    if line.startswith("- [ ]"):
                        acceptance_criteria.append(line[5:].strip())
                    elif line.startswith("-"):
                        acceptance_criteria.append(line[1:].strip())
        else:
            # Old structured format
            description = story_dict.get("description", "")
            acceptance_criteria = story_dict.get("acceptance_criteria", [])
            technical_spec = story_dict.get("technical_spec", {})

            # Build description with technical details
            full_description = f"{description}\n\n"
            full_description += f"**Story ID:** {story_id}\n"
            full_description += f"**Layer:** {layer}\n"

            if implements:
                full_description += f"**Implements:** {', '.join(implements)}\n"

            if technical_spec:
                full_description += "\n## Technical Specification\n\n"

                files_to_create = technical_spec.get("files_to_create") or []
                if files_to_create:
                    full_description += "**Files to create:**\n"
                    for f in files_to_create:
                        full_description += f"- `{f}`\n"

                deps = technical_spec.get("dependencies") or []
                if deps:
                    full_description += f"\n**Dependencies:** {', '.join(str(d) for d in deps)}\n"

                env_vars = technical_spec.get("environment_variables") or []
                if env_vars:
                    full_description += (
                        f"\n**Environment variables:** {', '.join(str(v) for v in env_vars)}\n"
                    )

                api_endpoint = technical_spec.get("api_endpoint")
                if api_endpoint:
                    full_description += f"\n**API:** `{api_endpoint}`\n"

                database_sql = technical_spec.get("database_sql")
                if database_sql:
                    full_description += "\n**Database:** Has SQL migration\n"

                key_notes = technical_spec.get("key_implementation_notes")
                if key_notes:
                    full_description += f"\n**Implementation Notes:** {key_notes}\n"

        # Create labels based on layer and implements
        labels = [f"layer-{layer}", "generated"]
        if implements:
            for imp in implements[:3]:  # Limit to first 3
                labels.append(imp)

        # Map story dependencies to backlog format
        dep_notes = ""
        if depends_on:
            dep_notes = f"\n**Depends on stories:** {', '.join(depends_on)}"

        try:
            draft_id = cli.create_draft(
                title=f"[{story_id}] {title}",
                description=full_description + dep_notes,
                priority="medium" if layer > 1 else "high",
                labels=labels,
                acceptance_criteria=acceptance_criteria,
            )

            if draft_id:
                draft_ids.append(draft_id)
                created_count += 1
                logger.info(f"Created draft {draft_id} for {story_id}: {title}")
            else:
                failed_count += 1
                logger.warning(f"Failed to create draft for {story_id}: {title}")

        except Exception as e:
            failed_count += 1
            logger.error(f"Error creating draft for {story_id}: {e}")

    return {
        "created_count": created_count,
        "failed_count": failed_count,
        "draft_ids": draft_ids,
    }


def create_backlog_drafts_after_ordering(session_manager: Any, output: str) -> None:
    """Create backlog drafts from story generation output after dependency ordering.

    This is wired as the additional_save callback for the dependency-ordering stage.
    Reads stories.json (structured data, preferred) or falls back to parsing markdown.
    """
    story_gen_dir = Path(session_manager.session_dir) / "story-generation"
    stories = []

    # Try stories.json first (structured output, no parsing needed)
    stories_json_file = story_gen_dir / "stories.json"
    if stories_json_file.exists():
        try:
            stories = json.loads(stories_json_file.read_text())
            logger.info(f"Loaded {len(stories)} stories from stories.json for backlog drafts")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to read stories.json: {e}")

    # Fallback: parse from markdown
    if not stories:
        story_gen_file = story_gen_dir / "story_generation.md"
        if not story_gen_file.exists():
            logger.warning(f"Story generation file not found at {story_gen_file}")
            return

        try:
            story_markdown = story_gen_file.read_text()
        except Exception as e:
            logger.error(f"Failed to read story generation file: {e}")
            return

        stories = parse_stories_from_markdown(story_markdown)

    if not stories:
        logger.warning("No stories found for backlog drafts")
        return

    # Get project directory (parent of session dir)
    project_dir = str(Path(session_manager.base_dir))

    # Create backlog drafts
    result = create_backlog_drafts_from_stories(stories, project_dir)
    logger.info(
        f"Backlog drafts: {result['created_count']} created, {result['failed_count']} failed"
    )
