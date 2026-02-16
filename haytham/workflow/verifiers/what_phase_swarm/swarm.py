"""WHAT phase verification (ADR-022).

Verifies MVP scope output against the concept anchor using a single
comprehensive verification agent that checks invariants, genericization,
and intent alignment.
"""

import logging
from typing import Any

from haytham.workflow.anchor_schema import ConceptAnchor
from haytham.workflow.verifiers.schemas import (
    GenericizationFlag,
    InvariantViolation,
    PhaseVerification,
)

logger = logging.getLogger(__name__)


def run_what_phase_swarm_verification(
    anchor: ConceptAnchor | None,
    anchor_str: str,
    phase_outputs: dict[str, str],
) -> PhaseVerification:
    """Run single-agent verification for WHAT phase.

    Simplified from multi-agent swarm to single comprehensive verification agent.
    The agent checks invariants, genericization, and intent alignment in one pass.

    Args:
        anchor: The structured concept anchor (may be None if only string available)
        anchor_str: Pre-formatted anchor string for display
        phase_outputs: Dict mapping stage slug to output content

    Returns:
        PhaseVerification with verification results including confidence score
    """
    from strands import Agent

    from haytham.agents.utils.model_provider import create_model

    logger.info("Starting WHAT phase single-agent verification")

    # Build verification prompt
    task = _build_single_agent_verification_prompt(anchor, anchor_str, phase_outputs)

    # Create a single verification agent
    try:
        model = create_model(max_tokens=4096, read_timeout=180.0)
        verifier = Agent(
            name="what_phase_verifier",
            system_prompt=_get_single_agent_system_prompt(),
            model=model,
        )
    except Exception as e:
        logger.error(f"Failed to create verification agent: {e}")
        return _fail_open_result(f"Agent creation failed: {e}")

    try:
        # Run verification
        result = verifier(task)

        # Extract text from result
        text_content = _extract_text_from_result(result)

        if text_content:
            parsed = _try_parse_json(text_content)
            if parsed:
                return _dict_to_phase_verification(parsed)

        # Fallback
        logger.warning("Could not parse verification results")
        return PhaseVerification(
            phase="WHAT",
            passed=True,
            confidence_score=30,
            confidence_rationale="Could not parse verification output",
            warnings=["Verification completed but output parsing failed"],
        )

    except Exception as e:
        logger.error(f"WHAT phase verification failed: {e}")
        return _fail_open_result(str(e))


def _get_single_agent_system_prompt() -> str:
    """Get the system prompt for single-agent verification."""
    return """You are a WHAT Phase Verifier. Your job is to verify MVP scope outputs against the concept anchor.

You must check THREE things:

1. **INVARIANT CHECK**: Are the anchor's invariants honored in the MVP scope?
   - For each invariant, find evidence it's preserved or violated
   - Violations that contradict the invariant are "blocking"
   - Missing explicit mention but not contradicted is "warning"

2. **GENERICIZATION CHECK**: Have distinctive features been replaced with generic patterns?
   - Check each identity feature from the anchor
   - Flag if specific terms became generic (e.g., "existing patients" → "users")

3. **INTENT ALIGNMENT CHECK**: Does the scope align with the founder's original intent?
   - Is the core goal preserved?
   - Are explicit constraints honored?
   - Have any non-goals crept in as features?

After your analysis, output ONLY a JSON code block with this EXACT format:

```json
{
  "phase": "WHAT",
  "passed": true,
  "confidence_score": 85,
  "confidence_rationale": "All invariants honored, no genericization detected",
  "invariants_honored": ["patient_base", "group_structure"],
  "invariants_violated": [],
  "identity_preserved": ["closed patient community"],
  "identity_genericized": [],
  "warnings": [],
  "notes": "Summary of findings"
}
```

For violations, use this format in the array:
{"invariant_name": "name", "violation_description": "what", "stage": "which", "severity": "blocking", "suggested_fix": "how"}

For genericizations:
{"original_feature": "specific", "generic_replacement": "generic", "stage": "which", "evidence": "quote"}

Be rigorous but fair. Output ONLY the JSON block, no other text."""


def _build_single_agent_verification_prompt(
    anchor: ConceptAnchor | None,
    anchor_str: str,
    phase_outputs: dict[str, str],
) -> str:
    """Build the verification prompt for single-agent verification."""
    # Format anchor section
    if anchor_str:
        anchor_section = anchor_str
    elif anchor:
        anchor_section = anchor.to_context_string()
    else:
        anchor_section = "(No anchor available)"

    # Format phase outputs
    outputs_section = []
    for stage_slug, output in phase_outputs.items():
        truncated = output[:4000] if len(output) > 4000 else output
        outputs_section.append(f"### {stage_slug}\n{truncated}")

    return f"""## Verification Task

Verify the WHAT phase outputs against the concept anchor.

{anchor_section}

---

## Phase Outputs to Verify

{chr(10).join(outputs_section)}

---

Analyze the outputs against the anchor. Check invariants, genericization, and intent alignment.
Output your findings as a JSON code block."""


def _fail_open_result(error_message: str) -> PhaseVerification:
    """Return a fail-open result when verification encounters errors.

    We fail open (pass=True) to avoid blocking the pipeline on verifier errors.
    The low confidence score signals that manual review is advisable.
    """
    truncated = error_message[:100] if len(error_message) > 100 else error_message
    return PhaseVerification(
        phase="WHAT",
        passed=True,  # Fail open - don't block pipeline
        confidence_score=10,  # Very low confidence due to error
        confidence_rationale=f"Verification error: {truncated}",
        warnings=[f"Verification error: {error_message}"],
    )


def _extract_text_from_result(result: Any) -> str:
    """Extract text content from an agent result."""
    from haytham.agents.output_utils import extract_text_from_result

    return extract_text_from_result(result)


def _try_parse_json(text: str) -> dict | None:
    """Try to extract and parse JSON from text content."""
    from haytham.agents.output_utils import extract_json_from_text

    return extract_json_from_text(text)


def _dict_to_phase_verification(data: dict) -> PhaseVerification:
    """Convert a dict to PhaseVerification with proper typing."""
    # Convert invariants_violated to InvariantViolation objects
    violations = []
    for v in data.get("invariants_violated", []):
        if isinstance(v, dict):
            try:
                violations.append(InvariantViolation(**v))
            except Exception as e:
                logger.warning(f"Failed to parse violation: {e}")
        elif isinstance(v, InvariantViolation):
            violations.append(v)

    # Convert identity_genericized to GenericizationFlag objects
    genericized = []
    for g in data.get("identity_genericized", []):
        if isinstance(g, dict):
            try:
                genericized.append(GenericizationFlag(**g))
            except Exception as e:
                logger.warning(f"Failed to parse genericization: {e}")
        elif isinstance(g, GenericizationFlag):
            genericized.append(g)

    # Determine passed status from violations
    has_blocking = any(v.severity == "blocking" for v in violations)
    passed = data.get("passed", not has_blocking)

    return PhaseVerification(
        phase="WHAT",
        passed=passed,
        confidence_score=data.get("confidence_score", 50),  # Default to medium if missing
        confidence_rationale=data.get(
            "confidence_rationale", "Confidence not reported by coordinator"
        ),
        invariants_honored=data.get("invariants_honored", []),
        invariants_violated=violations,
        identity_preserved=data.get("identity_preserved", []),
        identity_genericized=genericized,
        warnings=data.get("warnings", []),
        notes=data.get("notes", ""),
    )
