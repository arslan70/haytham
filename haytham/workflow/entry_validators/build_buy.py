"""Entry condition validator for Build vs Buy Analysis workflow."""

import logging
from typing import TYPE_CHECKING

from haytham.workflow.stage_registry import WorkflowType

from .base import EntryConditionResult, WorkflowEntryValidator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class BuildBuyAnalysisEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Build vs Buy Analysis workflow.

    Entry conditions:
    - MVP Specification workflow completed
    - At least 1 functional capability exists in VectorDB
    - Capability Model document exists
    - ADR-022: WHAT phase verification passes (scope fidelity, capability alignment)
    """

    workflow_type = WorkflowType.BUILD_BUY_ANALYSIS
    phase_name = "WHAT"

    def validate(self, force_override: bool = False) -> EntryConditionResult:
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

    def _check_mvp_specification_complete(self) -> bool:
        """Check if MVP Specification workflow is complete."""
        return self._check_workflow_complete("mvp-specification", "capability-model")

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
