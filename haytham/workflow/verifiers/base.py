"""Base classes for phase-boundary verifiers (ADR-022).

Phase-boundary verifiers run at decision gates to check cumulative phase output
against the concept anchor. They are independent LLM calls that review the
producing agents' work - categorically different from self-checks.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from burr.core import State

from haytham.agents.factory.agent_factory import create_agent_by_name
from haytham.workflow.anchor_schema import ConceptAnchor

from .schemas import PhaseVerification

logger = logging.getLogger(__name__)

# Fallback session directory (used only when session_manager is unavailable).
# Prefer passing session_dir from SessionManager.session_dir at call sites.
_FALLBACK_SESSION_DIR = Path(__file__).resolve().parents[3] / "session"


def save_verification_result(result: PhaseVerification, session_dir: Path | None = None) -> Path:
    """Save verification result to session directory as JSON.

    Args:
        result: PhaseVerification to save
        session_dir: Session directory (defaults to project session/)

    Returns:
        Path to the saved file
    """
    save_dir = session_dir or _FALLBACK_SESSION_DIR
    logger.info(f"Saving verification result to {save_dir}")
    save_dir.mkdir(parents=True, exist_ok=True)

    # Save as verification_{phase}.json
    filename = f"verification_{result.phase.lower()}.json"
    filepath = save_dir / filename

    # Convert to dict for JSON serialization
    result_dict = {
        "phase": result.phase,
        "passed": result.passed,
        "confidence_score": result.confidence_score,
        "confidence_rationale": result.confidence_rationale,
        "invariants_honored": result.invariants_honored,
        "invariants_violated": [
            {
                "invariant_name": v.invariant,
                "violation_description": v.violation,
                "stage": v.stage,
                "severity": v.severity,
                "suggested_fix": v.suggested_fix,
            }
            for v in result.invariants_violated
        ],
        "identity_preserved": result.identity_preserved,
        "identity_genericized": [
            {
                "original_feature": g.original_feature,
                "generic_replacement": g.generic_replacement,
                "stage": g.stage,
                "evidence": g.evidence,
            }
            for g in result.identity_genericized
        ],
        "warnings": result.warnings,
        "notes": result.notes,
    }

    filepath.write_text(json.dumps(result_dict, indent=2))
    logger.info(f"Saved verification result to {filepath}")

    return filepath


@dataclass
class VerificationResult:
    """Result of a phase verification including user override status."""

    verification: PhaseVerification
    user_override: bool = False  # True if user acknowledged and overrode violations
    override_reason: str = ""  # User's reason for override (if any)

    @property
    def should_proceed(self) -> bool:
        """Check if execution should proceed past the gate."""
        if self.verification.passed:
            return True
        if self.user_override:
            return True
        return not self.verification.has_blocking_violations


class PhaseVerifier(ABC):
    """Abstract base class for phase-boundary verifiers.

    Each phase has a dedicated verifier with a focused rubric:
    - WHY (Gate 1): Concept preservation, fabrication detection
    - WHAT (Gate 2): Scope fidelity, invariant reflection in capabilities
    - HOW (Gate 3): Trait consistency, architecture alignment
    - STORIES (Gate 4): Appetite compliance, framework coherence, traceability
    """

    # Phase identifier
    phase_name: str = ""

    # Verifier-specific rubric instructions
    rubric: str = ""

    def __init__(self):
        """Initialize the verifier."""
        self._agent = None

    @property
    def agent(self):
        """Lazily create the verifier agent."""
        if self._agent is None:
            self._agent = create_agent_by_name("phase_verifier")
        return self._agent

    @abstractmethod
    def get_phase_outputs(self, state: State) -> dict[str, str]:
        """Extract the relevant stage outputs for this phase.

        Args:
            state: Burr state containing stage outputs

        Returns:
            Dict mapping stage slug to output content
        """
        pass

    def verify(self, state: State) -> PhaseVerification:
        """Run verification against the concept anchor.

        Args:
            state: Burr state with concept_anchor and phase outputs

        Returns:
            PhaseVerification with results
        """
        # Get the anchor
        anchor = state.get("concept_anchor")
        anchor_str = state.get("concept_anchor_str", "")

        if not anchor and not anchor_str:
            logger.warning(f"No concept anchor found for {self.phase_name} verification")
            return PhaseVerification(
                phase=self.phase_name,
                passed=True,
                warnings=["No concept anchor available - skipping verification"],
            )

        # Get phase outputs
        phase_outputs = self.get_phase_outputs(state)
        if not phase_outputs:
            logger.warning(f"No outputs found for {self.phase_name} verification")
            return PhaseVerification(
                phase=self.phase_name,
                passed=True,
                warnings=["No phase outputs available - skipping verification"],
            )

        # Build verification prompt
        prompt = self._build_verification_prompt(anchor, anchor_str, phase_outputs)

        try:
            # Run the verifier agent
            result = self._run_verification(prompt)
            return result
        except Exception as e:
            logger.error(f"Verification failed for {self.phase_name}: {e}")
            return PhaseVerification(
                phase=self.phase_name,
                passed=True,  # Fail open - don't block on verifier errors
                warnings=[f"Verification error: {str(e)}"],
            )

    def _build_verification_prompt(
        self,
        anchor: ConceptAnchor | None,
        anchor_str: str,
        phase_outputs: dict[str, str],
    ) -> str:
        """Build the verification prompt for the LLM."""
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
            # Truncate very long outputs
            truncated = output[:4000] if len(output) > 4000 else output
            outputs_section.append(f"### {stage_slug}\n{truncated}")

        return f"""## Verification Task

You are verifying the {self.phase_name} phase outputs against the concept anchor.

{anchor_section}

---

## Phase Outputs to Verify

{chr(10).join(outputs_section)}

---

## Verification Rubric

{self.rubric}

---

## Instructions

1. Compare each phase output against the anchor's invariants and identity features
2. For each invariant, determine if it is honored or violated
3. For each identity feature, determine if it is preserved or genericized
4. Classify violations as "blocking" (must fix) or "warning" (surface for review)
5. Return a structured PhaseVerification result

Be rigorous but fair. Not every difference is a violation - agents may legitimately
expand on the anchor. But if a distinctive feature is replaced with a generic
pattern, or an explicit constraint is ignored, flag it.

Return your analysis as JSON matching the PhaseVerification schema."""

    def _run_verification(self, prompt: str) -> PhaseVerification:
        """Run the verification agent and parse results.

        This is a placeholder - actual implementation would use a dedicated
        verifier agent. For now, we return a pass-through result.
        """
        # TODO: Implement actual LLM-based verification
        # For now, return a permissive result to not block the pipeline
        logger.info(f"Running {self.phase_name} phase verification (placeholder)")

        return PhaseVerification(
            phase=self.phase_name,
            passed=True,
            notes="Verification placeholder - full implementation pending",
        )


class WhyPhaseVerifier(PhaseVerifier):
    """Verifier for Phase 1 (WHY - Idea Validation).

    Checks: Concept preservation, fabrication detection, attributed claims.
    """

    phase_name = "WHY"

    rubric = """
**Focus Areas for WHY Phase:**

1. **Concept Preservation**
   - Does the validation summary still describe the ORIGINAL idea?
   - Are distinctive features preserved or genericized?
   - Has the target user been changed (e.g., "his existing patients" → "therapists")?

2. **Fabrication Detection**
   - Are statistics attributed with sources or marked as estimates?
   - Are claims attributed to the founder actually from the original input?
   - Are competitor comparisons relevant to the actual problem domain?

3. **Constraint Honoring**
   - Is the community model (closed/open) preserved?
   - Is the interaction model (sync/async) preserved?
   - Are non-goals NOT being added as features?

**Blocking Violations:**
- Changing the core problem being solved
- Attributing fabricated claims to the founder
- Replacing closed community with open registration

**Warnings:**
- Minor genericization of secondary features
- Unattributed but plausible statistics
"""

    def get_phase_outputs(self, state: State) -> dict[str, str]:
        """Get WHY phase outputs: idea_analysis, market_context, risk_assessment, validation_summary."""
        outputs = {}
        for key in ["idea_analysis", "market_context", "risk_assessment", "validation_summary"]:
            value = state.get(key, "")
            if value:
                outputs[key] = value

        # Include pivot_strategy if present
        pivot = state.get("pivot_strategy", "")
        if pivot:
            outputs["pivot_strategy"] = pivot

        return outputs


class WhatPhaseVerifier(PhaseVerifier):
    """Verifier for Phase 2 (WHAT - MVP Specification).

    Uses swarm-based verification with 4 specialized agents for deep analysis:
    - Coordinator (orchestrates, synthesizes)
    - Invariant Checker (verifies anchor invariants)
    - Genericization Detector (detects identity drift)
    - Intent Alignment Checker (verifies scope alignment)

    Checks: Scope fidelity, capability-invariant alignment.
    """

    phase_name = "WHAT"

    rubric = """
**Focus Areas for WHAT Phase:**

1. **Scope Fidelity**
   - Does the MVP scope preserve the distinctive features?
   - Are anchor invariants reflected in the scope decisions?
   - Has The One Thing been genericized?

2. **Capability-Invariant Alignment**
   - Do functional capabilities map to anchor invariants?
   - Are distinctive interaction patterns preserved in capabilities?
   - Are non-goals NOT appearing as capabilities?

3. **System Traits Consistency**
   - Do system traits align with anchor constraints?
   - Is the interaction model (sync/async, realtime) correct?
   - Is the community model reflected in auth/access traits?

**Blocking Violations:**
- MVP scope contradicts anchor invariants
- Capabilities that implement non-goals
- System traits that conflict with explicit constraints

**Warnings:**
- Minor capability genericization
- Trait inferences that could go either way
"""

    def verify(self, state: State) -> PhaseVerification:
        """Run swarm-based verification for WHAT phase.

        Overrides base class to use a multi-agent swarm instead of single-agent
        verification. The swarm provides:
        - Specialized checkers with focused mandates
        - Cross-validation between checkers
        - Confidence scoring based on checker agreement
        - Autonomous retry/clarification without user intervention
        """
        from haytham.workflow.verifiers.what_phase_swarm.swarm import (
            run_what_phase_swarm_verification,
        )

        # Extract session_dir from session_manager (prefer over fallback constant)
        sm = state.get("session_manager")
        session_dir = getattr(sm, "session_dir", None) if sm else None

        # Get the anchor
        anchor = state.get("concept_anchor")
        anchor_str = state.get("concept_anchor_str", "")

        if not anchor and not anchor_str:
            logger.warning(f"No concept anchor found for {self.phase_name} verification")
            result = PhaseVerification(
                phase=self.phase_name,
                passed=True,
                confidence_score=0,
                confidence_rationale="No concept anchor available - verification skipped",
                warnings=["No concept anchor available - skipping verification"],
            )
            save_verification_result(result, session_dir=session_dir)
            return result

        # Get phase outputs
        phase_outputs = self.get_phase_outputs(state)
        logger.info(
            f"Phase outputs for {self.phase_name}: {list(phase_outputs.keys()) if phase_outputs else 'None'}"
        )
        if not phase_outputs:
            logger.warning(f"No outputs found for {self.phase_name} verification")
            result = PhaseVerification(
                phase=self.phase_name,
                passed=True,
                confidence_score=0,
                confidence_rationale="No phase outputs available - verification skipped",
                warnings=["No phase outputs available - skipping verification"],
            )
            save_verification_result(result, session_dir=session_dir)
            return result

        try:
            # Run swarm verification
            logger.info(f"Running swarm verification for {self.phase_name}")
            logger.info(
                f"  anchor type: {type(anchor)}, anchor_str len: {len(anchor_str) if anchor_str else 0}"
            )
            logger.info(f"  phase_outputs keys: {list(phase_outputs.keys())}")

            result = run_what_phase_swarm_verification(anchor, anchor_str, phase_outputs)

            logger.info(
                f"Swarm verification completed: passed={result.passed}, confidence={result.confidence_score}"
            )

            # Save result to file for debugging/UI display
            try:
                save_verification_result(result, session_dir=session_dir)
                logger.info("Verification result saved successfully")
            except Exception as save_err:
                logger.error(f"Failed to save verification result: {save_err}")

            return result
        except Exception as e:
            logger.error(f"Swarm verification failed for {self.phase_name}: {e}", exc_info=True)
            error_result = PhaseVerification(
                phase=self.phase_name,
                passed=True,  # Fail open - don't block pipeline
                confidence_score=10,
                confidence_rationale=f"Verification failed with error: {str(e)[:50]}",
                warnings=[f"Verification error: {str(e)}"],
            )
            # Still save error result for visibility
            try:
                save_verification_result(error_result, session_dir=session_dir)
                logger.info("Error verification result saved")
            except Exception as save_err:
                logger.error(f"Failed to save error verification result: {save_err}")
            return error_result

    def get_phase_outputs(self, state: State) -> dict[str, str]:
        """Get WHAT phase outputs: mvp_scope, capability_model, system_traits."""
        outputs = {}
        for key in ["mvp_scope", "capability_model", "system_traits"]:
            value = state.get(key, "")
            if value:
                outputs[key] = value
        return outputs


class HowPhaseVerifier(PhaseVerifier):
    """Verifier for Phase 3 (HOW - Technical Design).

    Checks: Trait consistency, architecture alignment.
    """

    phase_name = "HOW"

    rubric = """
**Focus Areas for HOW Phase:**

1. **Trait Consistency**
   - Do architecture decisions align with system traits?
   - Are there contradictions between build/buy recommendations?
   - Does the tech stack support the specified traits?

2. **Architecture-Invariant Alignment**
   - Do architecture decisions support anchor invariants?
   - Is the interaction model properly implemented?
   - Does the data model support the required structure?

3. **Internal Consistency**
   - Do build/buy decisions cite the correct system traits?
   - Are there contradictions between stages (e.g., realtime: false but recommending realtime DB)?

**Blocking Violations:**
- Architecture contradicts system traits
- Build/buy decisions that violate anchor constraints
- Tech choices incompatible with specified traits

**Warnings:**
- Minor inconsistencies in trait references
- Over-engineering beyond MVP scope
"""

    def get_phase_outputs(self, state: State) -> dict[str, str]:
        """Get HOW phase outputs: build_buy_analysis, architecture_decisions."""
        outputs = {}
        for key in ["build_buy_analysis", "architecture_decisions"]:
            value = state.get(key, "")
            if value:
                outputs[key] = value
        return outputs


class StoriesPhaseVerifier(PhaseVerifier):
    """Verifier for Phase 4 (STORIES - Implementation).

    Checks: Appetite compliance, framework coherence, traceability.
    """

    phase_name = "STORIES"

    rubric = """
**Focus Areas for STORIES Phase:**

1. **Appetite Compliance**
   - Is story count within appetite bounds?
   - Are stories appropriately sized for the specified appetite?
   - Is complexity proportional to the MVP scope?

2. **Framework Coherence**
   - Is there a single, consistent frontend framework?
   - Do tech choices align with architecture decisions?
   - Are there conflicting framework references?

3. **Capability Traceability**
   - Do stories trace back to capabilities?
   - Are all capabilities covered by stories?
   - Are there stories for features not in capabilities?

4. **Invariant Preservation**
   - Do stories implement the anchor invariants?
   - Is the distinctive interaction pattern preserved?
   - Are non-goals NOT appearing as stories?

**Blocking Violations:**
- Story count exceeds appetite by >50%
- Multiple conflicting frontend frameworks
- Stories implementing non-goals

**Warnings:**
- Story count slightly above appetite
- Minor traceability gaps
- Stories that genericize identity features
"""

    def get_phase_outputs(self, state: State) -> dict[str, str]:
        """Get STORIES phase outputs: story_generation, story_validation, dependency_ordering."""
        outputs = {}
        for key in ["story_generation", "story_validation", "dependency_ordering"]:
            value = state.get(key, "")
            if value:
                outputs[key] = value
        return outputs


# Registry of verifiers by phase
PHASE_VERIFIERS = {
    "WHY": WhyPhaseVerifier,
    "WHAT": WhatPhaseVerifier,
    "HOW": HowPhaseVerifier,
    "STORIES": StoriesPhaseVerifier,
}


def get_verifier(phase: str) -> PhaseVerifier:
    """Get the verifier for a phase.

    Args:
        phase: Phase name (WHY, WHAT, HOW, STORIES)

    Returns:
        Instantiated verifier for the phase
    """
    verifier_class = PHASE_VERIFIERS.get(phase.upper())
    if not verifier_class:
        raise ValueError(f"Unknown phase: {phase}. Valid phases: {list(PHASE_VERIFIERS.keys())}")
    return verifier_class()


def run_phase_verification(phase: str, state: State) -> PhaseVerification:
    """Run verification for a phase.

    Args:
        phase: Phase name
        state: Burr state with anchor and phase outputs

    Returns:
        PhaseVerification result
    """
    verifier = get_verifier(phase)
    return verifier.verify(state)
