"""Base classes for entry condition validators.

Provides SessionStateAdapter, EntryConditionResult, and WorkflowEntryValidator.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from haytham.workflow.stage_registry import WorkflowType

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
        anchor_file = self._session_manager.session_dir / "concept_anchor.json"
        if not anchor_file.exists():
            return None

        try:
            return json.loads(anchor_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
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
    Subclasses that require ADR-022 phase verification should set ``phase_name``
    (e.g. "WHY", "WHAT", "HOW").
    """

    workflow_type: WorkflowType
    phase_name: str | None = None

    def __init__(self, session_manager: "SessionManager"):
        """Initialize validator with session manager.

        Args:
            session_manager: SessionManager instance for loading state
        """
        self.session_manager = session_manager
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self, force_override: bool = False) -> EntryConditionResult:
        """Run all entry condition checks.

        Args:
            force_override: If True, allow proceeding despite a blocking
                recommendation (e.g. NO-GO).  Only used by validators
                that have overridable gates.

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

    # ------------------------------------------------------------------
    # Shared helpers (DRY: used by multiple subclasses)
    # ------------------------------------------------------------------

    def _run_phase_verification(self) -> dict[str, Any]:
        """Run ADR-022 phase verification using ``self.phase_name``.

        Returns:
            Dict with verification results
        """
        phase = self.phase_name
        if phase is None:
            return {"phase": None, "passed": True, "skipped": True}

        try:
            from haytham.workflow.verifiers.base import run_phase_verification

            state_adapter = SessionStateAdapter(self.session_manager)
            result = run_phase_verification(phase, state_adapter)

            for warning in result.warnings:
                self.warnings.append(f"[{phase} Phase] {warning}")

            for g in result.identity_genericized:
                self.warnings.append(
                    f"[{phase} Phase] Genericization detected: {g.original_feature} → {g.generic_replacement}"
                )

            for violation in result.blocking_violations:
                self.warnings.append(
                    f"[{phase} Phase BLOCKING] {violation.invariant}: {violation.violation}"
                )

            return {
                "phase": result.phase,
                "passed": result.passed,
                "warnings_count": len(result.warnings),
                "violations_count": len(result.invariants_violated),
                "genericizations_count": len(result.identity_genericized),
            }

        except (ImportError, TypeError, ValueError, AttributeError) as e:
            logger.warning(f"Phase verification failed (non-blocking): {e}")
            return {"phase": phase, "passed": True, "error": str(e)}

    def _check_workflow_complete(
        self,
        workflow_slug: str,
        final_stage_slug: str,
        *,
        legacy_slugs: tuple[str, ...] = (),
    ) -> bool:
        """Check if a prerequisite workflow is complete (3-tier fallback).

        1. ``session_manager.is_workflow_complete(workflow_slug)``
        2. ``stage_statuses[final_stage_slug] == "completed"``
        3. Lock file ``.{workflow_slug}.locked`` exists

        Args:
            workflow_slug: Workflow identifier (e.g. "idea-validation")
            final_stage_slug: Last stage in the workflow to check as fallback
            legacy_slugs: Additional workflow slugs to check (backward compat)

        Returns:
            True if the workflow is considered complete
        """
        # Primary check
        if self.session_manager.is_workflow_complete(workflow_slug):
            return True

        # Legacy slug checks
        for slug in legacy_slugs:
            if self.session_manager.is_workflow_complete(slug):
                return True

        # Fallback: stage status
        session = self.session_manager.load_session()
        if session:
            stage_statuses = session.get("stage_statuses", {})
            if stage_statuses.get(final_stage_slug) == "completed":
                self.warnings.append(
                    f"Workflow completion not recorded, but {final_stage_slug} stage is complete"
                )
                return True

        # Fallback: lock file
        lock_file = self.session_manager.session_dir / f".{workflow_slug}.locked"
        if lock_file.exists():
            self.warnings.append(
                f"Workflow completion not recorded, but {workflow_slug} was accepted by user"
            )
            return True

        self.errors.append(f"{workflow_slug.replace('-', ' ').title()} workflow is not complete")
        return False
