"""Concept Anchor Extraction (ADR-022).

Extracts a small, structured, immutable anchor from the original idea + concept expansion
output to prevent concept drift across the pipeline.

The anchor captures:
- Intent: What the founder asked for (goal, constraints, non-goals)
- Invariants: Properties that must remain true across all stages
- Identity: Distinctive features that differentiate this from generic solutions
"""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from haytham.agents.factory.agent_factory import create_agent_by_name
from haytham.workflow.anchor_schema import ConceptAnchor, ConceptHealth

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)


def extract_concept_anchor(
    system_goal: str,
    idea_analysis_output: str,
) -> ConceptAnchor:
    """Extract concept anchor from the original idea and concept expansion.

    Args:
        system_goal: The original startup idea from the founder
        idea_analysis_output: The output from the concept expansion stage

    Returns:
        ConceptAnchor with extracted invariants and identity features

    Raises:
        ValueError: If anchor extraction fails
    """
    # Create the anchor extractor agent with structured output
    agent = create_agent_by_name("anchor_extractor")

    # Build the extraction prompt
    prompt = f"""## Original Startup Idea (from Founder)
{system_goal}

## Concept Expansion Analysis
{idea_analysis_output[:3000]}

---

Extract the concept anchor from the above. Focus on:
1. What EXACTLY did the founder ask for? (not what you think is best)
2. What constraints did they state or strongly imply?
3. What makes this DIFFERENT from a generic startup pattern?

Return the structured ConceptAnchor."""

    # Run the agent
    result = agent(prompt)

    # 1. First check for Strands structured output (result.structured_output)
    # This is the primary path when structured_output_model is set
    if hasattr(result, "structured_output") and result.structured_output is not None:
        if isinstance(result.structured_output, ConceptAnchor):
            logger.info("Anchor extracted via Strands structured output")
            return result.structured_output
        # Strands might return a dict that needs validation
        if isinstance(result.structured_output, dict):
            try:
                anchor = ConceptAnchor.model_validate(result.structured_output)
                logger.info("Anchor extracted from Strands output dict")
                return anchor
            except ValidationError as e:
                logger.warning(f"Failed to validate Strands output dict: {e}")

    # 2. Fall back to parsing JSON from message content
    from haytham.agents.output_utils import extract_json_from_text, extract_text_from_result

    text = extract_text_from_result(result)
    if text.strip():
        data = extract_json_from_text(text)
        if data is not None:
            try:
                anchor = ConceptAnchor.model_validate(data)
                logger.info("Anchor extracted from message content JSON")
                return anchor
            except ValidationError as e:
                logger.warning(f"Failed to validate anchor from JSON: {e}")

    # 3. Fallback: create a minimal anchor
    logger.warning(
        "Anchor extraction returned non-structured output, creating minimal anchor. "
        f"Result type: {type(result)}, has structured_output: {hasattr(result, 'structured_output')}, "
        f"structured_output type: {type(getattr(result, 'structured_output', None))}"
    )
    return ConceptAnchor(
        intent={
            "goal": system_goal[:200],
            "explicit_constraints": [],
            "non_goals": [],
        },
        invariants=[],
        identity=[],
    )


_HEALTH_SIGNAL_RE = re.compile(
    r"\*\*(?P<key>Pain Clarity|Trigger Strength|Willingness to Pay Signal):\*\*\s*(?P<value>\S+)",
)


def _parse_concept_health(output: str) -> ConceptHealth | None:
    """Parse Concept Health Signals (Section 6) from concept expansion output.

    Returns None if the section is not present.
    """
    # Find Section 6 content
    section_match = re.search(
        r"##\s*6\.\s*Concept Health Signals(.*?)(?=\n##\s|\Z)",
        output,
        re.DOTALL,
    )
    if not section_match:
        return None

    section_text = section_match.group(1)
    signals: dict[str, str] = {}
    for m in _HEALTH_SIGNAL_RE.finditer(section_text):
        signals[m.group("key")] = m.group("value")

    if not signals:
        return None

    # Collect any notes (lines after the signal values that aren't blank or signal lines)
    notes_parts = []
    for line in section_text.strip().splitlines():
        line = line.strip().lstrip("- ")
        # Skip signal lines and empty lines
        if not line or _HEALTH_SIGNAL_RE.search(line) or line.startswith("**"):
            continue
        # Capture explanation text (e.g., "aspiration-driven, not pain-driven")
        if not line.startswith("#"):
            notes_parts.append(line)

    return ConceptHealth(
        pain_clarity=signals.get("Pain Clarity", ""),
        trigger_strength=signals.get("Trigger Strength", ""),
        willingness_to_pay=signals.get("Willingness to Pay Signal", ""),
        notes=" ".join(notes_parts)[:200] if notes_parts else "",
    )


def extract_anchor_post_processor(output: str, state: "State") -> dict[str, Any]:
    """Post-processor for idea-analysis stage that extracts the concept anchor.

    This runs after idea-analysis completes and:
    1. Extracts the anchor via LLM call
    2. Stores the anchor in Burr state for downstream stages
    3. Saves the anchor to disk for phase verifiers to access

    Args:
        output: The concept expansion output from the just-completed stage
        state: Current Burr state containing system_goal

    Returns:
        Dict with concept_anchor key for state update
    """
    system_goal = state.get("system_goal", "")
    # Use the output parameter directly - it contains the stage output
    # Note: state.get("idea_analysis") would return empty string because
    # the post_processor runs BEFORE state is updated with the new output
    idea_analysis = output if output else state.get("idea_analysis", "")

    if not system_goal:
        logger.warning("No system_goal in state, cannot extract anchor")
        return {}

    if not idea_analysis:
        logger.warning("No idea_analysis output available, cannot extract anchor")
        return {}

    try:
        anchor = extract_concept_anchor(system_goal, idea_analysis)

        # Inject concept health signals parsed directly from Section 6
        # (deterministic parsing — no LLM needed for this)
        health = _parse_concept_health(idea_analysis)
        if health:
            anchor.concept_health = health
            logger.info(
                f"Parsed concept health: pain={health.pain_clarity}, "
                f"trigger={health.trigger_strength}, wtp={health.willingness_to_pay}"
            )

        # Override archetype with user selection if provided
        user_archetype = state.get("archetype")
        if user_archetype:
            from haytham.workflow.anchor_schema import IdeaArchetype

            try:
                anchor.archetype = IdeaArchetype(user_archetype)
            except ValueError:
                pass  # LLM classification stands

        logger.info(
            f"Extracted concept anchor with {len(anchor.invariants)} invariants, "
            f"{len(anchor.identity)} identity features"
        )

        anchor_str = anchor.to_context_string()

        # Save anchor to disk for phase verifiers (ADR-022)
        session_manager = state.get("session_manager")
        if session_manager and hasattr(session_manager, "session_dir"):
            try:
                anchor_file = session_manager.session_dir / "concept_anchor.json"
                anchor_data = {
                    "anchor": anchor.model_dump(),
                    "anchor_str": anchor_str,
                }
                anchor_file.write_text(json.dumps(anchor_data, indent=2))
                logger.info(f"Saved concept anchor to {anchor_file}")
            except (OSError, TypeError, ValueError) as save_err:
                logger.error(f"Failed to save anchor file: {save_err}", exc_info=True)
        else:
            logger.warning("No session_manager in state - anchor file not saved to disk")

        # Store both the Pydantic model and its string representation in Burr state
        return {
            "concept_anchor": anchor,
            "concept_anchor_str": anchor_str,
        }
    except Exception as e:
        logger.error(f"Failed to extract concept anchor: {e}")
        return {}


def get_anchor_from_state(state: "State") -> ConceptAnchor | None:
    """Retrieve the concept anchor from state.

    Args:
        state: Burr state

    Returns:
        ConceptAnchor if available, None otherwise
    """
    anchor = state.get("concept_anchor")
    if isinstance(anchor, ConceptAnchor):
        return anchor
    return None


def get_anchor_context_string(state: "State") -> str:
    """Get the anchor as a formatted context string for agent prompts.

    Args:
        state: Burr state

    Returns:
        Formatted anchor string, or empty string if no anchor
    """
    # Prefer pre-computed string
    anchor_str = state.get("concept_anchor_str")
    if anchor_str:
        return anchor_str

    # Fall back to computing from anchor
    anchor = get_anchor_from_state(state)
    if anchor:
        return anchor.to_context_string()

    return ""
