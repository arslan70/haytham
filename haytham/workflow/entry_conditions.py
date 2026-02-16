"""Entry Condition Validators for Workflow Transitions.

This module provides centralized validation for workflow entry conditions,
ensuring all prerequisites are met before a workflow can start.

Each workflow has specific entry conditions:
- Idea Validation: No prerequisites (starting point)
- MVP Specification: Requires Idea Validation complete with GO/PIVOT recommendation
- Story Generation: Requires MVP Specification complete with capabilities

The validators check session state, stage outputs, and VectorDB to ensure
all required data is available for the next workflow.

ADR-022: Phase-boundary verifiers are integrated at each gate transition to
check cumulative phase output against the concept anchor before proceeding.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from haytham.phases.stage_config import WorkflowType

if TYPE_CHECKING:
    from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)


# =============================================================================
# ADR-022: State Adapter for Phase Verifiers
# =============================================================================


class SessionStateAdapter:
    """Adapts SessionManager to provide a State-like interface for verifiers.

    Phase verifiers expect a Burr State object with get() method. This adapter
    wraps SessionManager to provide that interface by loading stage outputs.
    """

    def __init__(self, session_manager: "SessionManager"):
        self._session_manager = session_manager
        self._cache: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key, loading from session if needed."""
        if key in self._cache:
            return self._cache[key]

        # Map state keys to stage outputs
        stage_mapping = {
            "idea_analysis": "idea-analysis",
            "market_context": "market-context",
            "risk_assessment": "risk-assessment",
            "validation_summary": "validation-summary",
            "pivot_strategy": "pivot-strategy",
            "mvp_scope": "mvp-scope",
            "capability_model": "capability-model",
            "system_traits": "system-traits",
            "build_buy_analysis": "build-buy-analysis",
            "architecture_decisions": "architecture-decisions",
            "story_generation": "story-generation",
            "story_validation": "story-validation",
            "dependency_ordering": "dependency-ordering",
        }

        if key in stage_mapping:
            stage_slug = stage_mapping[key]
            value = self._session_manager.load_stage_output(stage_slug)
            self._cache[key] = value
            return value if value else default

        # ADR-022: Concept anchor is stored in a separate file
        if key in ("concept_anchor", "concept_anchor_str"):
            anchor_data = self._load_concept_anchor()
            if anchor_data:
                if key == "concept_anchor_str":
                    value = anchor_data.get("anchor_str", "")
                else:
                    # Return the anchor dict (verifier will handle it)
                    value = anchor_data.get("anchor", {})
                self._cache[key] = value
                return value if value else default
            return default

        # System goal stored in session manifest
        if key == "system_goal":
            session = self._session_manager.load_session()
            if session:
                value = session.get(key)
                self._cache[key] = value
                return value if value else default

        return default

    def _load_concept_anchor(self) -> dict[str, Any] | None:
        """Load concept anchor from the session file."""
        import json

        anchor_file = self._session_manager.session_dir / "concept_anchor.json"
        if not anchor_file.exists():
            return None

        try:
            return json.loads(anchor_file.read_text())
        except Exception as e:
            logger.warning(f"Failed to load concept anchor file: {e}")
            return None


# =============================================================================
# Entry Condition Result
# =============================================================================


@dataclass
class EntryConditionResult:
    """Result of entry condition validation.

    Attributes:
        passed: Whether all entry conditions are met
        message: Human-readable summary message
        details: Detailed information about each check
        recommendation: For Idea Validation, the GO/NO-GO/PIVOT recommendation
        can_override: Whether user can override a failed validation
        override_warning: Warning message if user chooses to override
    """

    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    can_override: bool = False
    override_warning: str = ""


# =============================================================================
# Base Validator
# =============================================================================


class WorkflowEntryValidator:
    """Base class for workflow entry validation.

    Subclasses implement specific validation logic for each workflow type.
    """

    workflow_type: WorkflowType

    def __init__(self, session_manager: "SessionManager"):
        """Initialize validator with session manager.

        Args:
            session_manager: SessionManager instance for loading state
        """
        self.session_manager = session_manager
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> EntryConditionResult:
        """Run all entry condition checks.

        Returns:
            EntryConditionResult with pass/fail status and details

        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError("Subclasses must implement validate()")

    def _reset(self):
        """Reset errors and warnings for fresh validation."""
        self.errors = []
        self.warnings = []


# =============================================================================
# Workflow 1: Idea Validation Entry Validator
# =============================================================================


class IdeaValidationEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Idea Validation workflow.

    Entry conditions: None (this is the starting point).
    The only requirement is a system goal (startup idea) provided by the user.
    """

    workflow_type = WorkflowType.IDEA_VALIDATION

    def validate(self) -> EntryConditionResult:
        """Validate entry conditions for Idea Validation.

        Since this is the starting workflow, the only check is that
        we have a system goal (startup idea) to analyze.

        Returns:
            EntryConditionResult (always passes if called correctly)
        """
        self._reset()

        # Check for system goal
        system_goal = self.session_manager.get_system_goal()
        has_goal = bool(system_goal and len(system_goal.strip()) > 10)

        if not has_goal:
            self.warnings.append("No system goal found - user should provide a startup idea")

        return EntryConditionResult(
            passed=True,  # Always passes - this is the starting point
            message="Ready to start Idea Validation workflow.",
            details={
                "has_system_goal": has_goal,
                "warnings": self.warnings,
            },
        )


# =============================================================================
# Workflow 2: MVP Specification Entry Validator
# =============================================================================


class MVPSpecificationEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for MVP Specification workflow.

    Entry conditions:
    - Idea Validation workflow completed
    - Recommendation is GO or PIVOT (not NO-GO)
    - Validation Summary document exists
    - ADR-022: WHY phase verification passes (concept preserved, no fabrication)
    """

    workflow_type = WorkflowType.MVP_SPECIFICATION

    def validate(self, force_override: bool = False) -> EntryConditionResult:
        """Validate entry conditions for MVP Specification.

        Args:
            force_override: If True, allow proceeding despite NO-GO recommendation

        Returns:
            EntryConditionResult with pass/fail status and details
        """
        self._reset()

        # Check 1: Idea Validation complete
        idea_validation_complete = self._check_idea_validation_complete()

        # Check 2: Validation Summary exists
        validation_summary_exists = self._check_validation_summary()

        # Check 3: Recommendation is GO or PIVOT
        recommendation = self._extract_recommendation()
        recommendation_ok = recommendation in ("GO", "PIVOT", "PROCEED")

        # ADR-022: Gate 1 - Run WHY phase verification
        phase_verification = self._run_phase_verification()

        # NO-GO is overridable - user can proceed at their own risk
        can_override = False
        override_warning = ""

        if not recommendation_ok and recommendation:
            if force_override:
                # User chose to override - add warning but don't block
                self.warnings.append(
                    f"Proceeding despite {recommendation} recommendation (user override)."
                )
                recommendation_ok = True  # Allow proceeding
            else:
                # Not overriding - this is an overridable block
                can_override = True
                override_warning = (
                    f"The validation returned {recommendation}. You can still proceed, but consider:\n"
                    "• Refining the idea based on validation feedback\n"
                    "• Exploring pivot opportunities identified in the report\n"
                    "• Proceeding anyway if you believe the validation is too conservative"
                )
                self.errors.append(
                    f"Validation recommendation is {recommendation}. "
                    "Override available if you want to proceed anyway."
                )

        # Compile result
        passed = len(self.errors) == 0 and idea_validation_complete and validation_summary_exists

        if passed:
            message = f"All entry conditions met. Recommendation: {recommendation}"
        else:
            if can_override:
                message = f"Recommendation is {recommendation}. You can override and proceed, or refine your idea."
            else:
                message = f"Entry conditions not met: {'; '.join(self.errors)}"

        return EntryConditionResult(
            passed=passed,
            message=message,
            recommendation=recommendation,
            can_override=can_override,
            override_warning=override_warning,
            details={
                "idea_validation_complete": idea_validation_complete,
                "validation_summary_exists": validation_summary_exists,
                "recommendation": recommendation,
                "recommendation_ok": recommendation_ok,
                "phase_verification": phase_verification,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _run_phase_verification(self) -> dict[str, Any]:
        """Run WHY phase verification (ADR-022 Gate 1).

        Returns:
            Dict with verification results
        """
        try:
            from haytham.workflow.verifiers.base import run_phase_verification

            state_adapter = SessionStateAdapter(self.session_manager)
            result = run_phase_verification("WHY", state_adapter)

            # Surface warnings from verification
            for warning in result.warnings:
                self.warnings.append(f"[WHY Phase] {warning}")

            # Surface genericizations as warnings
            for g in result.identity_genericized:
                self.warnings.append(
                    f"[WHY Phase] Genericization detected: {g.original_feature} → {g.generic_replacement}"
                )

            # Blocking violations surface as warnings (user can override at gate)
            for violation in result.blocking_violations:
                self.warnings.append(
                    f"[WHY Phase BLOCKING] {violation.invariant}: {violation.violation}"
                )

            return {
                "phase": result.phase,
                "passed": result.passed,
                "warnings_count": len(result.warnings),
                "violations_count": len(result.invariants_violated),
                "genericizations_count": len(result.identity_genericized),
            }

        except Exception as e:
            logger.warning(f"Phase verification failed (non-blocking): {e}")
            return {"phase": "WHY", "passed": True, "error": str(e)}

    def _check_idea_validation_complete(self) -> bool:
        """Check if Idea Validation workflow is complete."""
        # Check for workflow completion record
        if self.session_manager.is_workflow_complete("idea-validation"):
            return True

        # Fallback: Check if validation-summary stage is complete
        session = self.session_manager.load_session()
        if session:
            stage_statuses = session.get("stage_statuses", {})
            if stage_statuses.get("validation-summary") == "completed":
                self.warnings.append(
                    "Workflow completion not recorded, but validation-summary stage is complete"
                )
                return True

        # Fallback: Check if user accepted results (lock file exists)
        lock_file = self.session_manager.session_dir / ".idea-validation.locked"
        if lock_file.exists():
            self.warnings.append(
                "Workflow completion not recorded, but idea-validation was accepted by user"
            )
            return True

        self.errors.append("Idea Validation workflow is not complete")
        return False

    def _check_validation_summary(self) -> bool:
        """Check that Validation Summary document exists."""
        validation_summary = self.session_manager.load_stage_output("validation-summary")

        if validation_summary and len(validation_summary.strip()) >= 100:
            return True

        # Fallback: Check risk-assessment output (last stage before summary)
        # This covers cases where the validation summary save failed but the
        # risk assessment completed successfully
        risk_assessment = self.session_manager.load_stage_output("risk-assessment")
        if risk_assessment and len(risk_assessment.strip()) >= 100:
            self.warnings.append(
                "Validation Summary not found, but risk-assessment output exists (used as fallback)"
            )
            return True

        self.errors.append("Validation Summary document not found")
        return False

    def _extract_recommendation(self) -> str:
        """Extract GO/NO-GO/PIVOT recommendation from validation summary.

        Short-circuit: checks recommendation.json metadata file first (written
        by save_final_output post_processor). Falls back to regex on markdown
        for backward compat with older sessions.

        Returns:
            Recommendation string or empty if not found
        """
        import json
        import re

        # Short-circuit: check metadata file from post_processor
        try:
            meta_path = self.session_manager.session_dir / "recommendation.json"
            if meta_path.exists():
                data = json.loads(meta_path.read_text())
                rec = data.get("recommendation", "")
                if rec in ("GO", "NO-GO", "PIVOT"):
                    logger.info(f"Recommendation from metadata: {rec}")
                    return rec
        except (json.JSONDecodeError, OSError, AttributeError):
            pass

        # Fallback: regex from rendered markdown on disk
        validation_summary = self.session_manager.load_stage_output("validation-summary")

        # Fallback to risk-assessment if validation-summary is empty
        if not validation_summary or len(validation_summary.strip()) < 50:
            validation_summary = self.session_manager.load_stage_output("risk-assessment")

        if not validation_summary:
            return ""

        summary_upper = validation_summary.upper()

        # Look for explicit "Recommendation:" line from ValidationSummaryOutput
        match = re.search(r"RECOMMENDATION:\s*(GO|NO-GO|PIVOT)", summary_upper)
        if match:
            recommendation = match.group(1)
            logger.info(f"Recommendation from markdown regex: {recommendation}")
            return recommendation

        # Fallback: Check for legacy patterns (for backward compatibility)
        if "VERDICT: GO" in summary_upper:
            return "GO"
        if "VERDICT: NO-GO" in summary_upper:
            return "NO-GO"
        if "VERDICT: PIVOT" in summary_upper:
            return "PIVOT"
        if "PROCEED WITH" in summary_upper or "READY TO PROCEED" in summary_upper:
            return "PROCEED"

        # Default to allowing progress if we can't determine
        self.warnings.append("Could not extract explicit recommendation from validation summary")
        return "PROCEED"


# =============================================================================
# Workflow 3a: Build vs Buy Analysis Entry Validator (Phase 3a: HOW)
# =============================================================================


class BuildBuyAnalysisEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Build vs Buy Analysis workflow.

    Entry conditions:
    - MVP Specification workflow completed
    - At least 1 functional capability exists in VectorDB
    - Capability Model document exists
    - ADR-022: WHAT phase verification passes (scope fidelity, capability alignment)
    """

    workflow_type = WorkflowType.BUILD_BUY_ANALYSIS

    def validate(self) -> EntryConditionResult:
        """Validate entry conditions for Build vs Buy Analysis.

        Returns:
            EntryConditionResult with pass/fail status and details
        """
        self._reset()

        # Check 1: MVP Specification complete
        mvp_spec_complete = self._check_mvp_specification_complete()

        # Check 2: Functional capabilities exist
        capability_count = self._check_functional_capabilities()

        # Check 3: Capability Model exists
        capability_model_exists = self._check_capability_model()

        # ADR-022: Gate 2 - Run WHAT phase verification
        phase_verification = self._run_phase_verification()

        # Compile result
        passed = len(self.errors) == 0

        if passed:
            message = f"All entry conditions met. {capability_count} functional capabilities found."
        else:
            message = f"Entry conditions not met: {'; '.join(self.errors)}"

        return EntryConditionResult(
            passed=passed,
            message=message,
            details={
                "mvp_spec_complete": mvp_spec_complete,
                "capability_count": capability_count,
                "capability_model_exists": capability_model_exists,
                "phase_verification": phase_verification,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _run_phase_verification(self) -> dict[str, Any]:
        """Run WHAT phase verification (ADR-022 Gate 2).

        Returns:
            Dict with verification results
        """
        try:
            from haytham.workflow.verifiers.base import run_phase_verification

            state_adapter = SessionStateAdapter(self.session_manager)
            result = run_phase_verification("WHAT", state_adapter)

            # Surface warnings from verification
            for warning in result.warnings:
                self.warnings.append(f"[WHAT Phase] {warning}")

            # Surface genericizations as warnings
            for g in result.identity_genericized:
                self.warnings.append(
                    f"[WHAT Phase] Genericization detected: {g.original_feature} → {g.generic_replacement}"
                )

            # Blocking violations surface as warnings (user can override at gate)
            for violation in result.blocking_violations:
                self.warnings.append(
                    f"[WHAT Phase BLOCKING] {violation.invariant}: {violation.violation}"
                )

            return {
                "phase": result.phase,
                "passed": result.passed,
                "warnings_count": len(result.warnings),
                "violations_count": len(result.invariants_violated),
                "genericizations_count": len(result.identity_genericized),
            }

        except Exception as e:
            logger.warning(f"Phase verification failed (non-blocking): {e}")
            return {"phase": "WHAT", "passed": True, "error": str(e)}

    def _check_mvp_specification_complete(self) -> bool:
        """Check if MVP Specification workflow is complete."""
        # Check for workflow completion record
        if self.session_manager.is_workflow_complete("mvp-specification"):
            return True

        # Fallback: Check if capability-model stage is complete
        session = self.session_manager.load_session()
        if session:
            stage_statuses = session.get("stage_statuses", {})
            if stage_statuses.get("capability-model") == "completed":
                self.warnings.append(
                    "Workflow completion not recorded, but capability-model stage is complete"
                )
                return True

        # Fallback: Check if user accepted results (lock file exists)
        lock_file = self.session_manager.session_dir / ".mvp-specification.locked"
        if lock_file.exists():
            self.warnings.append(
                "Workflow completion not recorded, but mvp-specification was accepted by user"
            )
            return True

        self.errors.append("MVP Specification workflow is not complete")
        return False

    def _check_functional_capabilities(self) -> int:
        """Check that at least 1 functional capability exists."""
        try:
            from haytham.state.vector_db import SystemStateDB

            db_path = self.session_manager.session_dir / "vector_db"
            if not db_path.exists():
                self.errors.append("VectorDB directory not found")
                return 0

            db = SystemStateDB(str(db_path))
            capabilities = db.get_capabilities()

            # Filter for functional capabilities
            functional_caps = [c for c in capabilities if c.get("subtype") == "functional"]

            if not functional_caps:
                self.errors.append("No functional capabilities found in VectorDB")
                return 0

            return len(functional_caps)

        except ImportError:
            self.warnings.append("VectorDB module not available - skipping capability check")
            return 0
        except Exception as e:
            self.errors.append(f"Failed to load capabilities: {e!s}")
            return 0

    def _check_capability_model(self) -> bool:
        """Check that Capability Model document exists."""
        capability_model = self.session_manager.load_stage_output("capability-model")

        if not capability_model:
            self.errors.append("Capability Model document not found")
            return False

        if len(capability_model.strip()) < 100:
            self.warnings.append("Capability Model document seems too short")

        return True


# =============================================================================
# Workflow 3b: Architecture Decisions Entry Validator (Phase 3b: HOW)
# =============================================================================


class ArchitectureDecisionsEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Architecture Decisions workflow.

    Entry conditions:
    - Build vs Buy Analysis workflow completed
    - Build vs Buy Analysis document exists
    - Capability Model document exists
    """

    workflow_type = WorkflowType.ARCHITECTURE_DECISIONS

    def validate(self) -> EntryConditionResult:
        """Validate entry conditions for Architecture Decisions.

        Returns:
            EntryConditionResult with pass/fail status and details
        """
        self._reset()

        # Check 1: Build vs Buy Analysis complete
        build_buy_complete = self._check_build_buy_complete()

        # Check 2: Build vs Buy Analysis document exists
        build_buy_exists = self._check_build_buy_analysis()

        # Check 3: Capability Model exists
        capability_model_exists = self._check_capability_model()

        # Compile result
        passed = len(self.errors) == 0

        if passed:
            message = "All entry conditions met. Ready to define architecture decisions."
        else:
            message = f"Entry conditions not met: {'; '.join(self.errors)}"

        return EntryConditionResult(
            passed=passed,
            message=message,
            details={
                "build_buy_complete": build_buy_complete,
                "build_buy_exists": build_buy_exists,
                "capability_model_exists": capability_model_exists,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _check_build_buy_complete(self) -> bool:
        """Check if Build vs Buy Analysis workflow is complete."""
        # Check for workflow completion record
        if self.session_manager.is_workflow_complete("build-buy-analysis"):
            return True

        # Fallback: Check if build-buy-analysis stage is complete
        session = self.session_manager.load_session()
        if session:
            stage_statuses = session.get("stage_statuses", {})
            if stage_statuses.get("build-buy-analysis") == "completed":
                self.warnings.append(
                    "Workflow completion not recorded, but build-buy-analysis stage is complete"
                )
                return True

        # Fallback: Check if user accepted results (lock file exists)
        lock_file = self.session_manager.session_dir / ".build-buy-analysis.locked"
        if lock_file.exists():
            self.warnings.append(
                "Workflow completion not recorded, but build-buy-analysis was accepted by user"
            )
            return True

        self.errors.append("Build vs Buy Analysis workflow is not complete")
        return False

    def _check_build_buy_analysis(self) -> bool:
        """Check that Build vs Buy Analysis document exists."""
        build_buy = self.session_manager.load_stage_output("build-buy-analysis")

        if not build_buy:
            self.errors.append("Build vs Buy Analysis document not found")
            return False

        if len(build_buy.strip()) < 100:
            self.warnings.append("Build vs Buy Analysis document seems too short")

        return True

    def _check_capability_model(self) -> bool:
        """Check that Capability Model document exists."""
        capability_model = self.session_manager.load_stage_output("capability-model")

        if not capability_model:
            self.errors.append("Capability Model document not found")
            return False

        return True


# =============================================================================
# Workflow 4: Story Generation Entry Validator (Phase 4: STORIES)
# =============================================================================


class StoryGenerationEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Story Generation workflow.

    Entry conditions:
    - Architecture Decisions workflow completed
    - Build vs Buy Analysis document exists
    - Architecture Decisions document exists
    - ADR-022: HOW phase verification passes (trait consistency, architecture alignment)
    """

    workflow_type = WorkflowType.STORY_GENERATION

    def validate(self) -> EntryConditionResult:
        """Validate entry conditions for Story Generation.

        Returns:
            EntryConditionResult with pass/fail status and details
        """
        self._reset()

        # Check 1: Architecture Decisions complete
        architecture_complete = self._check_architecture_decisions_complete()

        # Check 2: Build vs Buy Analysis exists
        build_buy_exists = self._check_build_buy_analysis()

        # Check 3: Architecture Decisions exists
        architecture_exists = self._check_architecture_decisions()

        # ADR-022: Gate 3 - Run HOW phase verification
        phase_verification = self._run_phase_verification()

        # Compile result
        passed = len(self.errors) == 0

        if passed:
            message = "All entry conditions met. Ready to generate stories."
        else:
            message = f"Entry conditions not met: {'; '.join(self.errors)}"

        return EntryConditionResult(
            passed=passed,
            message=message,
            details={
                "architecture_complete": architecture_complete,
                "build_buy_exists": build_buy_exists,
                "architecture_exists": architecture_exists,
                "phase_verification": phase_verification,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _run_phase_verification(self) -> dict[str, Any]:
        """Run HOW phase verification (ADR-022 Gate 3).

        Returns:
            Dict with verification results
        """
        try:
            from haytham.workflow.verifiers.base import run_phase_verification

            state_adapter = SessionStateAdapter(self.session_manager)
            result = run_phase_verification("HOW", state_adapter)

            # Surface warnings from verification
            for warning in result.warnings:
                self.warnings.append(f"[HOW Phase] {warning}")

            # Surface genericizations as warnings
            for g in result.identity_genericized:
                self.warnings.append(
                    f"[HOW Phase] Genericization detected: {g.original_feature} → {g.generic_replacement}"
                )

            # Blocking violations surface as warnings (user can override at gate)
            for violation in result.blocking_violations:
                self.warnings.append(
                    f"[HOW Phase BLOCKING] {violation.invariant}: {violation.violation}"
                )

            return {
                "phase": result.phase,
                "passed": result.passed,
                "warnings_count": len(result.warnings),
                "violations_count": len(result.invariants_violated),
                "genericizations_count": len(result.identity_genericized),
            }

        except Exception as e:
            logger.warning(f"Phase verification failed (non-blocking): {e}")
            return {"phase": "HOW", "passed": True, "error": str(e)}

    def _check_architecture_decisions_complete(self) -> bool:
        """Check if Architecture Decisions workflow is complete."""
        # Check for new workflow completion record
        if self.session_manager.is_workflow_complete("architecture-decisions"):
            return True

        # Also check legacy technical-design workflow for backward compatibility
        if self.session_manager.is_workflow_complete("technical-design"):
            return True

        # Fallback: Check if architecture-decisions stage is complete
        session = self.session_manager.load_session()
        if session:
            stage_statuses = session.get("stage_statuses", {})
            if stage_statuses.get("architecture-decisions") == "completed":
                self.warnings.append(
                    "Workflow completion not recorded, but architecture-decisions stage is complete"
                )
                return True

        # Fallback: Check if user accepted results (lock file exists)
        lock_file = self.session_manager.session_dir / ".architecture-decisions.locked"
        if lock_file.exists():
            self.warnings.append(
                "Workflow completion not recorded, but architecture-decisions was accepted by user"
            )
            return True

        self.errors.append("Architecture Decisions workflow is not complete")
        return False

    def _check_build_buy_analysis(self) -> bool:
        """Check that Build vs Buy Analysis document exists."""
        build_buy = self.session_manager.load_stage_output("build-buy-analysis")

        if not build_buy:
            self.errors.append("Build vs Buy Analysis document not found")
            return False

        if len(build_buy.strip()) < 100:
            self.warnings.append("Build vs Buy Analysis document seems too short")

        return True

    def _check_architecture_decisions(self) -> bool:
        """Check that Architecture Decisions document exists."""
        architecture = self.session_manager.load_stage_output("architecture-decisions")

        if not architecture:
            self.errors.append("Architecture Decisions document not found")
            return False

        if len(architecture.strip()) < 100:
            self.warnings.append("Architecture Decisions document seems too short")

        return True


# =============================================================================
# Validator Factory
# =============================================================================

_VALIDATORS: dict[WorkflowType, type[WorkflowEntryValidator]] = {
    WorkflowType.IDEA_VALIDATION: IdeaValidationEntryValidator,
    WorkflowType.MVP_SPECIFICATION: MVPSpecificationEntryValidator,
    WorkflowType.BUILD_BUY_ANALYSIS: BuildBuyAnalysisEntryValidator,
    WorkflowType.ARCHITECTURE_DECISIONS: ArchitectureDecisionsEntryValidator,
    WorkflowType.STORY_GENERATION: StoryGenerationEntryValidator,
}


def get_entry_validator(
    workflow_type: WorkflowType, session_manager: "SessionManager"
) -> WorkflowEntryValidator:
    """Get the appropriate entry validator for a workflow type.

    Args:
        workflow_type: The workflow to validate entry for
        session_manager: SessionManager instance for state access

    Returns:
        Configured WorkflowEntryValidator instance

    Raises:
        ValueError: If workflow_type is not recognized
    """
    validator_class = _VALIDATORS.get(workflow_type)
    if validator_class is None:
        raise ValueError(f"No validator registered for workflow type: {workflow_type}")
    return validator_class(session_manager)


def validate_workflow_entry(
    workflow_type: WorkflowType,
    session_manager: "SessionManager",
    force_override: bool = False,
) -> EntryConditionResult:
    """Convenience function to validate entry conditions for a workflow.

    Args:
        workflow_type: The workflow to validate entry for
        session_manager: SessionManager instance for state access
        force_override: If True, allow overriding soft blocks (like NO-GO)

    Returns:
        EntryConditionResult with validation outcome
    """
    validator = get_entry_validator(workflow_type, session_manager)

    # All validators accept force_override as a keyword argument;
    # those that don't use it simply ignore it via **kwargs or default.
    try:
        return validator.validate(force_override=force_override)
    except TypeError:
        # Fallback for validators that don't accept force_override
        return validator.validate()


# =============================================================================
# Workflow Availability Check
# =============================================================================


def get_available_workflows(session_manager: "SessionManager") -> list[WorkflowType]:
    """Get list of workflows that can be started based on current state.

    This is useful for determining what actions to show in the UI.

    Args:
        session_manager: SessionManager instance

    Returns:
        List of WorkflowType values that have all entry conditions met
    """
    available = []

    for workflow_type in WorkflowType:
        try:
            result = validate_workflow_entry(workflow_type, session_manager)
            if result.passed:
                available.append(workflow_type)
        except Exception as e:
            logger.warning(f"Error checking availability for {workflow_type}: {e}")

    return available


def get_next_available_workflow(session_manager: "SessionManager") -> WorkflowType | None:
    """Get the next workflow in sequence that can be started.

    Checks workflows in order and returns the first one that:
    1. Has entry conditions met
    2. Is not yet completed

    Args:
        session_manager: SessionManager instance

    Returns:
        WorkflowType for next available workflow, or None if all complete/unavailable
    """
    workflow_order = [
        WorkflowType.IDEA_VALIDATION,
        WorkflowType.MVP_SPECIFICATION,
        WorkflowType.BUILD_BUY_ANALYSIS,
        WorkflowType.ARCHITECTURE_DECISIONS,
        WorkflowType.STORY_GENERATION,
    ]

    for workflow_type in workflow_order:
        # Skip if already complete
        if session_manager.is_workflow_complete(workflow_type.value):
            continue

        # Check if entry conditions are met
        result = validate_workflow_entry(workflow_type, session_manager)
        if result.passed:
            return workflow_type

    return None
