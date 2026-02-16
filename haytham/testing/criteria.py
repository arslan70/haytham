"""Per-agent rubrics and test case definitions for LLM-as-Judge evaluation (ADR-018).

Each agent has a rubric string for OutputEvaluator, a pass threshold, and
a list of upstream fixture filenames required to build its test cases.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from strands_evals import Case

logger = logging.getLogger(__name__)

# Test idea labels for readable output
IDEA_LABELS = {
    "T1": "Web App",
    "T2": "CLI Tool",
    "T3": "API Service",
    "T4": "Marketplace",
    "T5": "Mobile App",
    "T6": "Wellness App (Power of 8)",  # ADR-022: Concept fidelity regression test
}


@dataclass
class AgentTestConfig:
    """Configuration for testing a single agent."""

    agent_name: str
    rubric: str
    pass_threshold: float
    upstream_fixtures: list[str] = field(default_factory=list)


# =============================================================================
# Agent Rubrics
# =============================================================================

# =============================================================================
# ADR-022: Concept Fidelity Rubrics
# =============================================================================

CONCEPT_FIDELITY_RUBRIC = """Evaluate the pipeline output for concept fidelity against the original idea.

**Concept Anchor Reference:**
The original idea should have explicit constraints and distinctive features that must be preserved.
Check if the output honors these or has genericized them.

**Scoring Criteria:**

Score 5 (EXCELLENT):
- All anchor invariants are preserved in the output
- All identity features are recognizable and not genericized
- No silent genericization or scope drift
- Distinctive elements remain distinctive

Score 4 (GOOD):
- All invariants are preserved
- Minor genericization of non-critical identity features
- Any genericization is flagged by verifier warnings

Score 3 (ACCEPTABLE):
- One invariant violated WITH explicit justification (InvariantOverride)
- Identity features are partially preserved
- Core concept is still recognizable

Score 2 (POOR):
- One or more invariants silently violated (no justification)
- Core identity features genericized without flagging
- Output drifts from original concept

Score 1 (FAIL):
- Final output describes a fundamentally different product than the input idea
- Major concept drift has occurred
- Original distinctive features are completely lost

**Key Questions:**
1. Would the founder recognize this as THEIR idea?
2. Are closed communities still closed, or opened up?
3. Are synchronous interactions still synchronous, or made async?
4. Is the target audience preserved, or expanded to generic users?
5. Are distinctive features preserved, or replaced with common patterns?

Provide a score from 1-5 with detailed reasoning for each criterion."""

ANCHOR_QUALITY_RUBRIC = """Evaluate the quality of the extracted concept anchor.

**An anchor should capture:**
1. Intent: The user's actual goal (not what we think they should build)
2. Invariants: Properties that MUST remain true across all stages
3. Identity: What makes this idea DIFFERENT from generic patterns

**Scoring Criteria:**

Score 5 (EXCELLENT):
- All explicit constraints from the input are captured
- Invariants match verifiable statements in the original input
- Non-goals are reasonable inferences (not contradicting user intent)
- Identity features are genuinely distinctive
- Source quotes are accurate

Score 4 (GOOD):
- Constraints are captured
- One non-goal is debatable but not harmful
- Identity features are mostly distinctive

Score 3 (ACCEPTABLE):
- One explicit constraint is missed
- OR one invariant is over-inferred (not clearly in input)
- Most key elements are present

Score 2 (POOR):
- Multiple constraints are missed
- OR non-goals contradict user intent
- Invariants don't match the input

Score 1 (FAIL):
- Anchor describes a different idea than the input
- Major misunderstanding of user intent
- Would constrain the pipeline incorrectly

**Key Questions:**
1. Does the goal capture what THEY want, not what's "better"?
2. Can every invariant be traced to a quote from the input?
3. Would removing any invariant allow building something fundamentally different?
4. Are non-goals reasonable inferences, not impositions?
5. Are identity features actually at risk of genericization?

Provide a score from 1-5 with detailed reasoning."""


AGENT_RUBRICS: dict[str, AgentTestConfig] = {
    # ADR-022: Anchor extractor evaluation
    "anchor_extractor": AgentTestConfig(
        agent_name="anchor_extractor",
        rubric=ANCHOR_QUALITY_RUBRIC,
        pass_threshold=0.8,  # 4/5 minimum
        upstream_fixtures=[],  # Uses original idea directly
    ),
    # ADR-022: End-to-end concept fidelity evaluation
    "concept_fidelity": AgentTestConfig(
        agent_name="concept_fidelity",
        rubric=CONCEPT_FIDELITY_RUBRIC,
        pass_threshold=0.8,  # 4/5 minimum - concept drift is a hard failure
        upstream_fixtures=[
            "concept-anchor.json",
            "validation-summary.md",
            "mvp-scope.md",
            "capability-model.md",
            "story-generation.md",
        ],
    ),
    "concept_expansion": AgentTestConfig(
        agent_name="concept_expansion",
        rubric="""Evaluate the agent output against these criteria:
1. Output includes a clear problem statement that identifies a specific pain point
2. Target user persona is defined with demographics or behavioral characteristics
3. Unique value proposition differentiates from existing alternatives
4. Use cases are concrete and actionable (not vague or generic)
5. Output is structured with clear sections and logical flow

Score 1.0 if all 5 criteria are met.
Score 0.75 if 4 criteria are met.
Score 0.5 if 3 criteria are met.
Score 0.25 if 2 criteria are met.
Score 0.0 if 1 or fewer criteria are met.""",
        pass_threshold=0.75,
        upstream_fixtures=[],
    ),
    "capability_model": AgentTestConfig(
        agent_name="capability_model",
        rubric="""Evaluate the agent output against these criteria:
1. Output is valid JSON with a 'capabilities' key containing 'functional' and 'non_functional' arrays
2. Every functional capability has an id with CAP-F-* prefix, a name, and a description
3. Every non-functional capability has an id with CAP-NF-* prefix, a name, and a description
4. Each capability includes a 'serves_scope_item' or 'rationale' field tracing it to the MVP scope
5. The number of functional capabilities is between 3 and 7 (focused MVP)
6. No capability duplicates or contradicts another

Score 1.0 if all 6 criteria are met.
Score 0.8 if 5 criteria are met.
Score 0.6 if 4 criteria are met.
Score 0.4 if 3 criteria are met.
Score 0.2 if 2 or fewer criteria are met.""",
        pass_threshold=1.0,
        upstream_fixtures=["mvp-scope.md"],
    ),
    "story_generator": AgentTestConfig(
        agent_name="story_generator",
        rubric="""Evaluate the agent output against these criteria:
1. Stories are organized into layers (Layer 0 for foundation, Layer 1+ for features)
2. Each story has a unique STORY-NNN identifier and a descriptive title
3. Each story references which capabilities it implements (CAP-F-* or CAP-NF-*)
4. Stories include acceptance criteria that are testable
5. Dependencies between stories are declared and form a valid DAG (no circular deps)
6. Layer 0 includes project initialization, database schema, and core configuration
7. All functional capabilities from the input are covered by at least one story

Score 1.0 if all 7 criteria are met.
Score 0.85 if 6 criteria are met.
Score 0.7 if 5 criteria are met.
Score 0.55 if 4 criteria are met.
Score 0.4 if 3 or fewer criteria are met.""",
        pass_threshold=1.0,
        upstream_fixtures=[
            "mvp-scope.md",
            "capability-model.md",
            "architecture-decisions.md",
            "build-buy-analysis.md",
        ],
    ),
    "system_traits": AgentTestConfig(
        agent_name="system_traits",
        rubric="""Evaluate the agent output against these criteria:
1. Output contains all 5 traits: interface, auth, deployment, data_layer, realtime
2. Each trait has a valid value from the allowed set (interface: browser/terminal/mobile_native/desktop_gui/api_only/none; auth: multi_user/single_user/none; deployment: cloud_hosted/app_store/package_registry/local_install/embedded; data_layer: remote_db/local_storage/file_system/none; realtime: true/false)
3. Multi-select traits (interface, deployment) use comma-separated list in brackets
4. Each trait has a one-sentence justification referencing specific capabilities or scope
5. Trait values are appropriate for the given idea (e.g., CLI tool should NOT have interface: [browser])
6. Output follows the expected markdown format with ## SYSTEM TRAITS header

Score 1.0 if all 6 criteria are met.
Score 0.8 if 5 criteria are met.
Score 0.6 if 4 criteria are met.
Score 0.4 if 3 criteria are met.
Score 0.2 if 2 or fewer criteria are met.""",
        pass_threshold=0.8,
        upstream_fixtures=["mvp-scope.md", "capability-model.md"],
    ),
}


# =============================================================================
# Test Case Builders
# =============================================================================


def _load_ideas(ideas_file: Path | None = None) -> list[dict]:
    """Load test ideas from the fixture file."""
    if ideas_file is None:
        ideas_file = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "test_ideas.json"

    with open(ideas_file) as f:
        data = json.load(f)
    return data["ideas"]


def _load_fixture(fixtures_dir: Path, idea_id: str, filename: str) -> str | None:
    """Load an upstream fixture file, returning None if missing."""
    fixture_path = fixtures_dir / idea_id / filename
    if not fixture_path.exists():
        return None
    return fixture_path.read_text()


def build_concept_expansion_cases(idea_ids: list[str]) -> list[Case]:
    """Build test cases for concept_expansion agent. No upstream fixtures needed."""
    ideas = _load_ideas()
    ideas_by_id = {idea["id"]: idea for idea in ideas}

    cases = []
    for idea_id in idea_ids:
        idea = ideas_by_id.get(idea_id)
        if idea is None:
            logger.warning(f"Unknown idea ID: {idea_id}, skipping")
            continue

        cases.append(
            Case(
                input=idea["idea"],
                expected_output="",  # Judge evaluates quality, not exact match
                metadata={"idea_id": idea_id, "category": idea["category"]},
            )
        )
    return cases


def build_capability_model_cases(
    idea_ids: list[str],
    fixtures_dir: Path,
) -> list[Case]:
    """Build test cases for capability_model agent.

    Requires mvp-scope.md upstream fixture. Builds context matching
    the format used in stage_executor.py (capability-model stage).
    """
    ideas = _load_ideas()
    ideas_by_id = {idea["id"]: idea for idea in ideas}

    cases = []
    for idea_id in idea_ids:
        idea = ideas_by_id.get(idea_id)
        if idea is None:
            logger.warning(f"Unknown idea ID: {idea_id}, skipping")
            continue

        mvp_scope = _load_fixture(fixtures_dir, idea_id, "mvp-scope.md")
        if mvp_scope is None:
            logger.warning(
                f"Missing fixture upstream_outputs/{idea_id}/mvp-scope.md — "
                f"skipping capability_model for {idea_id}"
            )
            continue

        # Build context matching stage_executor.py:278-287
        context_str = f"## Startup Idea\n{idea['idea']}\n\n"
        context_str += (
            f"## MVP Scope (PRIMARY INPUT - trace all capabilities to this)\n{mvp_scope}\n\n"
        )
        context_str += (
            "IMPORTANT: Your capabilities MUST trace to the IN SCOPE items listed above. "
            "Do NOT invent scope items. Quote actual IN SCOPE items in serves_scope_item.\n"
        )

        cases.append(
            Case(
                input=context_str,
                expected_output="",
                metadata={"idea_id": idea_id, "category": idea["category"]},
            )
        )
    return cases


def build_system_traits_cases(
    idea_ids: list[str],
    fixtures_dir: Path,
) -> list[Case]:
    """Build test cases for system_traits agent.

    Requires mvp-scope.md and capability-model.md upstream fixtures.
    Builds context matching what the stage executor assembles.
    """
    ideas = _load_ideas()
    ideas_by_id = {idea["id"]: idea for idea in ideas}

    cases = []
    for idea_id in idea_ids:
        idea = ideas_by_id.get(idea_id)
        if idea is None:
            logger.warning(f"Unknown idea ID: {idea_id}, skipping")
            continue

        mvp_scope = _load_fixture(fixtures_dir, idea_id, "mvp-scope.md")
        capability_model = _load_fixture(fixtures_dir, idea_id, "capability-model.md")

        missing = []
        if mvp_scope is None:
            missing.append("mvp-scope.md")
        if capability_model is None:
            missing.append("capability-model.md")

        if missing:
            logger.warning(f"Missing fixtures for system_traits/{idea_id}: {missing} — skipping")
            continue

        # Build context matching stage_executor.py system-traits handling
        context_str = f"## Startup Idea\n{idea['idea']}\n\n"
        context_str += f"## MVP Scope\n{mvp_scope}\n\n"
        context_str += f"## Capability Model\n{capability_model}\n\n"
        context_str += "Classify the system traits based on the above context.\n"

        cases.append(
            Case(
                input=context_str,
                expected_output="",
                metadata={"idea_id": idea_id, "category": idea["category"]},
            )
        )
    return cases


def build_story_generator_cases(
    idea_ids: list[str],
    fixtures_dir: Path,
) -> list[Case]:
    """Build test cases for story_generator (uses run_story_swarm).

    Requires all 4 upstream fixtures. Upstream outputs are stored in
    Case.metadata for the task function to unpack.
    """
    ideas = _load_ideas()
    ideas_by_id = {idea["id"]: idea for idea in ideas}

    cases = []
    for idea_id in idea_ids:
        idea = ideas_by_id.get(idea_id)
        if idea is None:
            logger.warning(f"Unknown idea ID: {idea_id}, skipping")
            continue

        required = [
            "mvp-scope.md",
            "capability-model.md",
            "architecture-decisions.md",
            "build-buy-analysis.md",
        ]
        fixtures = {}
        missing = []
        for filename in required:
            content = _load_fixture(fixtures_dir, idea_id, filename)
            if content is None:
                missing.append(filename)
            else:
                # Convert filename to key: "mvp-scope.md" -> "mvp_scope"
                key = filename.replace(".md", "").replace("-", "_")
                fixtures[key] = content

        if missing:
            logger.warning(f"Missing fixtures for story_generator/{idea_id}: {missing} — skipping")
            continue

        # Input is a summary for the evaluator to see; actual data is in metadata
        input_summary = (
            f"Generate implementation stories for: {idea['idea']}\n\n"
            f"Based on MVP scope, capability model, architecture decisions, "
            f"and build/buy analysis provided as upstream context."
        )

        cases.append(
            Case(
                input=input_summary,
                expected_output="",
                metadata={
                    "idea_id": idea_id,
                    "category": idea["category"],
                    "system_goal": idea["idea"],
                    **fixtures,
                },
            )
        )
    return cases


# =============================================================================
# ADR-022: Concept Fidelity Case Builders
# =============================================================================


def build_anchor_extractor_cases(idea_ids: list[str]) -> list[Case]:
    """Build test cases for anchor_extractor evaluation.

    Uses the original idea directly - no upstream fixtures needed.
    The judge evaluates whether the extracted anchor properly captures
    the idea's invariants and identity features.
    """
    ideas = _load_ideas()
    ideas_by_id = {idea["id"]: idea for idea in ideas}

    cases = []
    for idea_id in idea_ids:
        idea = ideas_by_id.get(idea_id)
        if idea is None:
            logger.warning(f"Unknown idea ID: {idea_id}, skipping")
            continue

        # Include concept fidelity anchors if present (for T6 and future ideas)
        metadata = {
            "idea_id": idea_id,
            "category": idea["category"],
        }

        # T6 and similar ideas have explicit fidelity anchors for validation
        if "concept_fidelity_anchors" in idea:
            metadata["expected_anchors"] = idea["concept_fidelity_anchors"]

        cases.append(
            Case(
                input=idea["idea"],
                expected_output="",  # Judge evaluates quality
                metadata=metadata,
            )
        )
    return cases


def build_concept_fidelity_cases(
    idea_ids: list[str],
    fixtures_dir: Path,
) -> list[Case]:
    """Build test cases for end-to-end concept fidelity evaluation.

    Requires pipeline outputs (anchor, validation summary, MVP scope,
    capability model, stories) to evaluate whether the original concept
    was preserved across the full pipeline.
    """
    ideas = _load_ideas()
    ideas_by_id = {idea["id"]: idea for idea in ideas}

    cases = []
    for idea_id in idea_ids:
        idea = ideas_by_id.get(idea_id)
        if idea is None:
            logger.warning(f"Unknown idea ID: {idea_id}, skipping")
            continue

        required = [
            "concept-anchor.json",
            "validation-summary.md",
            "mvp-scope.md",
            "capability-model.md",
            "story-generation.md",
        ]
        fixtures = {}
        missing = []
        for filename in required:
            content = _load_fixture(fixtures_dir, idea_id, filename)
            if content is None:
                missing.append(filename)
            else:
                key = filename.replace(".md", "").replace(".json", "").replace("-", "_")
                fixtures[key] = content

        if missing:
            logger.warning(f"Missing fixtures for concept_fidelity/{idea_id}: {missing} — skipping")
            continue

        # Build evaluation context showing original idea + final outputs
        input_context = f"""## Original Idea (Source of Truth)
{idea["idea"]}

## Concept Anchor (Extracted Invariants)
{fixtures.get("concept_anchor", "Not available")}

## Final Pipeline Outputs

### Validation Summary
{fixtures.get("validation_summary", "Not available")[:2000]}

### MVP Scope
{fixtures.get("mvp_scope", "Not available")[:2000]}

### Capability Model
{fixtures.get("capability_model", "Not available")[:2000]}

### Story Generation (First 10 stories)
{fixtures.get("story_generation", "Not available")[:3000]}
"""

        metadata = {
            "idea_id": idea_id,
            "category": idea["category"],
            "system_goal": idea["idea"],
        }

        # Include expected anchors for ideas that have them defined
        if "concept_fidelity_anchors" in idea:
            metadata["expected_anchors"] = idea["concept_fidelity_anchors"]

        cases.append(
            Case(
                input=input_context,
                expected_output="",
                metadata=metadata,
            )
        )
    return cases
