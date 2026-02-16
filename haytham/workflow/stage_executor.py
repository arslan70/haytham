"""Stage Executor Framework for Burr Actions.

This module provides a generic stage execution framework that eliminates
the boilerplate duplication across stage actions.

Design Principles:
- Template Method Pattern: Common execution flow with customization points
- Open/Closed: New stages don't require new action functions
- DRY: All common logic in one place
- Observability: OpenTelemetry tracing via stage_span

Domain-specific orchestration functions live in :mod:`haytham.workflow.stages`.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from burr.core import State

from .agent_runner import (
    _extract_agent_output,
    run_agent,
    run_parallel_agents,
    save_stage_output,
)
from .stage_registry import get_stage_registry

logger = logging.getLogger(__name__)


# =============================================================================
# Stage Execution Configuration
# =============================================================================


@dataclass
class StageExecutionConfig:
    """Configuration for executing a stage.

    This replaces the hardcoded logic in individual action functions.
    """

    # Stage identifier (used to look up metadata from registry)
    stage_slug: str

    # Query template (can include {system_goal} placeholder)
    query_template: str

    # For parallel execution: list of agent configs
    # Each config is {"name": "agent_name", "query": "query string"}
    parallel_agents: list[dict[str, str]] | None = None

    # Post-processor for output (e.g., extract risk level)
    post_processor: Callable[[str, State], dict[str, Any]] | None = None

    # Additional save operations (e.g., save_final_output)
    additional_save: Callable[[Any, str], None] | None = None

    # Custom agent factory (for stages that don't use run_agent)
    custom_agent_factory: Callable[[], Any] | None = None

    # Custom context builder (if stage needs special context handling)
    custom_context_builder: Callable[[State], dict[str, Any]] | None = None

    # Programmatic executor (for stages that don't need LLM agents)
    # Takes State and returns (output: str, status: str)
    programmatic_executor: Callable[[State], tuple[str, str]] | None = None

    # ADR-022: Enable context retrieval tools for stages that need deep context
    # When True, agents can use tools to selectively retrieve full upstream outputs
    use_context_tools: bool = False

    # ADR-022 Part 2: Post-validators for cross-stage consistency checks
    # Each validator takes (output: str, state: State) and returns list[str] of warnings
    # Warnings are logged and can be surfaced to users at decision gates
    post_validators: list[Callable[[str, State], list[str]]] | None = None

    # Pydantic model class for JSON↔markdown split.
    # When set, the executor stores raw output (JSON) in Burr state for pipeline
    # consumption, but renders markdown via output_model.to_markdown() for disk save.
    output_model: type | None = None


# =============================================================================
# Stage Executor
# =============================================================================


class StageExecutor:
    """Executes a stage using the provided configuration.

    This class encapsulates the common execution pattern:
    1. Check if already completed (idempotent)
    2. Log execution start
    3. Build context from previous stages
    4. Execute agent(s)
    5. Process output
    6. Save results
    7. Update state
    """

    def __init__(self, config: StageExecutionConfig):
        """Initialize the executor.

        Args:
            config: Stage execution configuration
        """
        self.config = config
        self.registry = get_stage_registry()
        self.stage = self.registry.get_by_slug(config.stage_slug)

    def execute(self, state: State) -> State:
        """Execute the stage.

        Args:
            state: Current Burr state

        Returns:
            Updated state with stage outputs
        """
        # Import telemetry (lazy to avoid circular imports)
        try:
            from haytham.telemetry import stage_span
        except ImportError:
            # Telemetry not available - use no-op context manager
            from contextlib import nullcontext

            def stage_span(*args, **kwargs):
                return nullcontext()

        # 1. Idempotent check - skip if already completed
        if self._is_already_completed(state):
            logger.info(f"{self.stage.display_name} already completed - skipping")
            return state.update(current_stage=self.stage.slug)

        # 2. Execute within a stage span for observability
        start_time = time.time()

        with stage_span(
            stage_slug=self.stage.slug,
            stage_name=self.stage.display_name,
            workflow_type=self.stage.workflow_type.value,
            agent_names=self.stage.agent_names,
            execution_mode=self.stage.execution_mode,
        ) as span:
            # 3. Log execution start
            self._log_start()

            # 4. Get common inputs
            system_goal = state["system_goal"]
            session_manager = state.get("session_manager")

            # 5. Build context
            context = self._build_context(state, system_goal)

            # 6. Execute agent(s) or programmatic logic
            if self.config.programmatic_executor:
                # Programmatic stages don't use LLM agents
                output, status = self.config.programmatic_executor(state)
            elif self.config.custom_agent_factory:
                output, status = self._execute_custom_agent(context, system_goal, state)
            elif self.config.parallel_agents:
                output, status = self._execute_parallel(context, session_manager)
            else:
                output, status = self._execute_single(context, session_manager, system_goal)

            # Record execution time
            execution_time = time.time() - start_time
            if hasattr(span, "set_attribute"):
                span.set_attribute("stage.duration_seconds", execution_time)
                span.set_attribute("stage.status", status)
                span.set_attribute("stage.output_length", len(output) if output else 0)

            # 7. Post-process output if needed
            extra_state_updates = {}
            if self.config.post_processor:
                extra_state_updates = self.config.post_processor(output, state)
                # Record extracted values (e.g., risk_level)
                for key, value in extra_state_updates.items():
                    if hasattr(span, "set_attribute"):
                        span.set_attribute(f"stage.{key}", str(value))

            # 7b. ADR-022: Run post-validators for cross-stage consistency
            validation_warnings = []
            if self.config.post_validators and output:
                for validator in self.config.post_validators:
                    try:
                        warnings = validator(output, state)
                        validation_warnings.extend(warnings)
                    except Exception as e:
                        logger.warning(f"Post-validator failed: {e}")

                if validation_warnings:
                    logger.warning(
                        f"Stage {self.stage.slug} validation warnings:\n"
                        + "\n".join(f"  - {w}" for w in validation_warnings)
                    )
                    # Store warnings in state for decision gate surfacing
                    extra_state_updates["validation_warnings"] = validation_warnings
                    if hasattr(span, "set_attribute"):
                        span.set_attribute("stage.validation_warnings", len(validation_warnings))

            # 8. Save output
            # When output_model is set, output is JSON — render markdown for disk
            display_output = output  # What gets written to disk (markdown)
            if session_manager and status == "completed":
                if self.config.output_model and output:
                    try:
                        display_output = self.config.output_model.model_validate_json(
                            output
                        ).to_markdown()
                    except Exception as e:
                        logger.warning(
                            f"Stage {self.stage.slug}: Failed to render markdown from output_model: {e}. "
                            "Saving raw output instead."
                        )
                        display_output = output  # Ensure display_output is set even on failure
                    self._save_output(session_manager, display_output)
                else:
                    self._save_output(session_manager, output)

                # Additional save operations (receive rendered markdown, not raw JSON)
                if self.config.additional_save:
                    self.config.additional_save(session_manager, display_output)
            else:
                # Log why save was skipped - this helps diagnose file persistence issues
                if not session_manager:
                    logger.warning(
                        f"Stage {self.stage.slug}: Skipping file save - session_manager is None/falsy"
                    )
                elif status != "completed":
                    logger.warning(
                        f"Stage {self.stage.slug}: Skipping file save - status is '{status}' (not 'completed')"
                    )

            logger.info(
                f"Stage {self.stage.slug} completed in {execution_time:.2f}s "
                f"(status={status}, output_length={len(output) if output else 0})"
            )

        # 9. Return updated state
        return state.update(
            **{self.stage.state_key: output},
            **{self.stage.status_key: status},
            current_stage=self.stage.slug,
            **extra_state_updates,
        )

    def _is_already_completed(self, state: State) -> bool:
        """Check if stage is already completed."""
        status = state.get(self.stage.status_key)
        output = state.get(self.stage.state_key)
        return status == "completed" and bool(output)

    def _log_start(self) -> None:
        """Log stage execution start."""
        logger.info("=" * 60)
        logger.info(f"Executing {self.stage.display_name}")
        logger.info("=" * 60)

    def _build_context(self, state: State, system_goal: str) -> dict[str, Any]:
        """Build context from previous stages.

        ADR-022: The concept anchor is always included in full for downstream stages.
        It is small (~500 tokens) by design and carries the information that
        truncation would otherwise destroy.
        """
        if self.config.custom_context_builder:
            # Custom context builders should also include the anchor
            context = self.config.custom_context_builder(state)
            # Inject anchor if not already present
            if "concept_anchor" not in context:
                anchor_str = state.get("concept_anchor_str", "")
                if anchor_str:
                    context["concept_anchor"] = anchor_str
            return context

        context = {"system_goal": system_goal}

        # ADR-022: Always include concept anchor for downstream stages (non-truncatable)
        # The anchor is small (~500 tokens) and carries critical invariants
        anchor_str = state.get("concept_anchor_str", "")
        if anchor_str and self.stage.slug != "idea-analysis":
            # Include anchor for all stages after idea-analysis
            context["concept_anchor"] = anchor_str

        # Add outputs from required context stages
        for slug in self.stage.required_context:
            stage_meta = self.registry.get_by_slug_safe(slug)
            if stage_meta:
                value = state.get(stage_meta.state_key, "")
                if value:
                    context[stage_meta.state_key] = value

        # Also include pivot_strategy if it exists (special case)
        if state.get("pivot_strategy"):
            context["pivot_strategy"] = state["pivot_strategy"]

        return context

    def _execute_single(
        self,
        context: dict[str, Any],
        session_manager: Any,
        system_goal: str,
    ) -> tuple[str, str]:
        """Execute a single agent."""
        query = self.config.query_template.format(system_goal=system_goal)
        agent_name = self.stage.agent_names[0] if self.stage.agent_names else "unknown"

        # ADR-022: Pass use_context_tools to enable selective context retrieval
        # When output_model is set, request JSON output from structured agents
        result = run_agent(
            agent_name,
            query,
            context,
            session_manager,
            use_context_tools=self.config.use_context_tools,
            output_as_json=self.config.output_model is not None,
        )
        return result["output"], result["status"]

    def _execute_parallel(
        self,
        context: dict[str, Any],
        session_manager: Any,
    ) -> tuple[str, str]:
        """Execute multiple agents in parallel."""
        # ADR-022: Pass use_context_tools to enable selective context retrieval
        results = run_parallel_agents(
            self.config.parallel_agents,
            context,
            session_manager,
            use_context_tools=self.config.use_context_tools,
        )

        # Combine outputs
        combined_output = ""
        all_completed = True

        for agent_name, result in results.items():
            combined_output += f"\n\n## {agent_name.replace('_', ' ').title()}\n\n"
            combined_output += result.get("output", "No output")

            if result.get("status") != "completed":
                all_completed = False

            # Save individual outputs
            if session_manager and result.get("status") == "completed":
                save_stage_output(
                    session_manager,
                    stage_slug=self.stage.slug,
                    agent_name=agent_name,
                    output=result["output"],
                )

        status = "completed" if all_completed else "partial"
        return combined_output.strip(), status

    def _execute_custom_agent(
        self,
        context: dict[str, Any],
        system_goal: str,
        state: State,
    ) -> tuple[str, str]:
        """Execute a custom agent using the context built by the stage's context builder.

        The context dict may contain two special keys set by the context builder:
        - ``_error``: If present, short-circuits with a failure message.
        - ``_context_str``: The fully-formatted prompt string for the agent.
        """
        # Short-circuit if the context builder flagged an error
        error = context.get("_error")
        if error:
            return error, "failed"

        try:
            agent = self.config.custom_agent_factory()
            context_str = context.get("_context_str", f"## Startup Idea\n{system_goal}\n\n")

            result_raw = agent(context_str)
            output = _extract_agent_output(
                result_raw, output_as_json=self.config.output_model is not None
            )
            return output, "completed"

        except Exception as e:
            logger.error(f"Custom agent failed: {e}")
            return f"Error: {str(e)}", "failed"

    def _save_output(self, session_manager: Any, output: str) -> None:
        """Save stage output."""
        agent_name = self.stage.agent_names[0] if self.stage.agent_names else "output"

        # For parallel stages, individual outputs are saved in _execute_parallel
        if not self.config.parallel_agents:
            save_stage_output(
                session_manager,
                stage_slug=self.stage.slug,
                agent_name=agent_name,
                output=output,
            )


# =============================================================================
# Entry Points
# =============================================================================


# Import STAGE_CONFIGS from the stages package (lazy to avoid circular import
# at module-parse time — configs.py imports StageExecutionConfig from here).
_STAGE_CONFIGS: dict[str, StageExecutionConfig] | None = None


def _get_stage_configs() -> dict[str, StageExecutionConfig]:
    global _STAGE_CONFIGS
    if _STAGE_CONFIGS is None:
        from .stages.configs import STAGE_CONFIGS

        _STAGE_CONFIGS = STAGE_CONFIGS
    return _STAGE_CONFIGS


def get_stage_executor(stage_slug: str) -> StageExecutor:
    """Get executor for a stage.

    Args:
        stage_slug: Stage slug (e.g., "idea-analysis")

    Returns:
        StageExecutor configured for the stage

    Raises:
        KeyError: If stage not found
    """
    configs = _get_stage_configs()
    if stage_slug not in configs:
        raise KeyError(f"No executor config for stage: {stage_slug}")
    return StageExecutor(configs[stage_slug])


def execute_stage(stage_slug: str, state: State) -> State:
    """Execute a stage by slug.

    Convenience function for direct execution.

    Args:
        stage_slug: Stage slug
        state: Current Burr state

    Returns:
        Updated state
    """
    executor = get_stage_executor(stage_slug)
    return executor.execute(state)
