"""
Stage-level logging for unified workflow execution.

DEPRECATED: This module is deprecated in favor of OpenTelemetry-based observability.
Use haytham.telemetry instead for stage-level tracing.

Migration guide:
    # Old (deprecated)
    from haytham.agents.utils.phase_logger import StageLogger, get_stage_logger

    # New (recommended)
    from haytham.telemetry import stage_span, record_stage_event

    with stage_span("idea-analysis", "Idea Analysis") as span:
        # Stage execution is automatically traced
        span.set_attribute("stage.custom_metric", 123)
        record_stage_event(span, "checkpoint_created", data={"key": "value"})

This module is kept for backward compatibility and will be removed in a future version.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class StageLogEntry:
    """Structured log entry for stage-level events.

    Simplified for single-session architecture - no project_id or session_id.
    """

    timestamp: str
    stage_slug: str
    stage_name: str
    event_type: str  # 'stage_start', 'stage_complete', 'stage_fail', 'checkpoint', 'user_feedback', 'change_request', 'agent_execution'
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class StageLogger:
    """
    Stage-level logger for tracking workflow execution.

    Simplified for single-session architecture - uses fixed session/ directory.

    Organizes logs by stage:
        session/logs/
        ├── idea-refinement/
        │   ├── stage_events.jsonl       # Stage lifecycle events
        │   ├── agent_executions.jsonl   # Agent execution logs
        │   ├── user_feedback.jsonl      # User feedback events
        │   └── metrics.json             # Stage metrics summary
        ├── market-analysis/
        │   └── ...
        └── session_summary.json         # Overall session metrics
    """

    def __init__(self, base_log_dir: str | Path | None = None):
        """
        Initialize stage logger.

        Args:
            base_log_dir: Base directory for logs (default: "session/logs")
        """
        if base_log_dir is None:
            self.base_log_dir = Path("session") / "logs"
        else:
            self.base_log_dir = Path(base_log_dir)
        self.base_log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"StageLogger initialized with base_log_dir: {self.base_log_dir}")

    def _get_stage_dir(self, stage_slug: str) -> Path:
        """Get stage log directory, creating if needed."""
        stage_dir = self.base_log_dir / stage_slug
        stage_dir.mkdir(parents=True, exist_ok=True)
        return stage_dir

    def _write_jsonl(self, file_path: Path, entry: StageLogEntry) -> None:
        """
        Write log entry to JSONL file (one JSON object per line).

        Args:
            file_path: Path to JSONL file
            entry: Log entry to write
        """
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write log entry to {file_path}: {e}")

    def _write_json(self, file_path: Path, data: dict[str, Any]) -> None:
        """
        Write data to JSON file.

        Args:
            file_path: Path to JSON file
            data: Data to write
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write JSON to {file_path}: {e}")

    def log_stage_start(
        self,
        stage_slug: str,
        stage_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log stage start event.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            stage_name: Stage name (e.g., "Idea Refinement")
            metadata: Optional metadata (execution_mode, required_context, etc.)
        """
        stage_dir = self._get_stage_dir(stage_slug)

        entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_slug=stage_slug,
            stage_name=stage_name,
            event_type="stage_start",
            data={"status": "in_progress", **(metadata or {})},
        )

        # Write to stage events log
        events_file = stage_dir / "stage_events.jsonl"
        self._write_jsonl(events_file, entry)

        logger.info(f"Stage '{stage_name}' ({stage_slug}) started")

    def log_stage_complete(
        self,
        stage_slug: str,
        stage_name: str,
        duration_seconds: float,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """
        Log stage completion event.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            stage_name: Stage name (e.g., "Idea Refinement")
            duration_seconds: Stage execution duration
            metrics: Optional metrics (tokens, cost, agent_count, etc.)
        """
        stage_dir = self._get_stage_dir(stage_slug)

        entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_slug=stage_slug,
            stage_name=stage_name,
            event_type="stage_complete",
            data={"status": "completed", "duration_seconds": duration_seconds, **(metrics or {})},
        )

        # Write to stage events log
        events_file = stage_dir / "stage_events.jsonl"
        self._write_jsonl(events_file, entry)

        # Write metrics summary
        metrics_data = {
            "stage_slug": stage_slug,
            "stage_name": stage_name,
            "status": "completed",
            "duration_seconds": duration_seconds,
            "completed_at": datetime.now().isoformat(),
            **(metrics or {}),
        }
        metrics_file = stage_dir / "metrics.json"
        self._write_json(metrics_file, metrics_data)

        logger.info(f"Stage '{stage_name}' ({stage_slug}) completed in {duration_seconds:.2f}s")

    def log_stage_fail(
        self,
        stage_slug: str,
        stage_name: str,
        error: Exception,
        duration_seconds: float | None = None,
        context: str | None = None,
    ) -> None:
        """
        Log stage failure event.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            stage_name: Stage name (e.g., "Idea Refinement")
            error: Exception that caused failure
            duration_seconds: Stage execution duration before failure
            context: Optional context description
        """
        stage_dir = self._get_stage_dir(stage_slug)

        entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_slug=stage_slug,
            stage_name=stage_name,
            event_type="stage_fail",
            data={
                "status": "failed",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
                "duration_seconds": duration_seconds,
            },
        )

        # Write to stage events log
        events_file = stage_dir / "stage_events.jsonl"
        self._write_jsonl(events_file, entry)

        # Write metrics summary with failure info
        metrics_data = {
            "stage_slug": stage_slug,
            "stage_name": stage_name,
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failed_at": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
        }
        metrics_file = stage_dir / "metrics.json"
        self._write_json(metrics_file, metrics_data)

        logger.error(f"Stage '{stage_name}' ({stage_slug}) failed: {type(error).__name__}: {error}")

    def log_checkpoint(
        self,
        stage_slug: str,
        stage_name: str,
        checkpoint_data: dict[str, Any],
    ) -> None:
        """
        Log checkpoint creation event.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            stage_name: Stage name (e.g., "Idea Refinement")
            checkpoint_data: Checkpoint data (status, outputs, metrics, etc.)
        """
        stage_dir = self._get_stage_dir(stage_slug)

        entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_slug=stage_slug,
            stage_name=stage_name,
            event_type="checkpoint",
            data=checkpoint_data,
        )

        # Write to stage events log
        events_file = stage_dir / "stage_events.jsonl"
        self._write_jsonl(events_file, entry)

        logger.info(f"Checkpoint created for stage '{stage_name}' ({stage_slug})")

    def log_user_feedback(
        self,
        stage_slug: str,
        stage_name: str,
        action: str,  # 'approve', 'request_changes', 'skip'
        feedback: dict[str, Any] | None = None,
    ) -> None:
        """
        Log user feedback event.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            stage_name: Stage name (e.g., "Idea Refinement")
            action: User action ('approve', 'request_changes', 'skip')
            feedback: Optional feedback data (comments, requested_changes, etc.)
        """
        stage_dir = self._get_stage_dir(stage_slug)

        entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_slug=stage_slug,
            stage_name=stage_name,
            event_type="user_feedback",
            data={"action": action, **(feedback or {})},
        )

        # Write to user feedback log
        feedback_file = stage_dir / "user_feedback.jsonl"
        self._write_jsonl(feedback_file, entry)

        logger.info(f"User feedback logged for stage '{stage_name}' ({stage_slug}): {action}")

    def log_change_request(
        self,
        stage_slug: str,
        stage_name: str,
        change_type: str,  # 'modify_prompt', 'provide_guidance', 'retry_with_same'
        change_data: dict[str, Any],
    ) -> None:
        """
        Log change request event.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            stage_name: Stage name (e.g., "Idea Refinement")
            change_type: Type of change request
            change_data: Change request data (modified_prompt, guidance, retry_count, etc.)
        """
        stage_dir = self._get_stage_dir(stage_slug)

        entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_slug=stage_slug,
            stage_name=stage_name,
            event_type="change_request",
            data={"change_type": change_type, **change_data},
        )

        # Write to user feedback log (change requests are a type of feedback)
        feedback_file = stage_dir / "user_feedback.jsonl"
        self._write_jsonl(feedback_file, entry)

        logger.info(f"Change request logged for stage '{stage_name}' ({stage_slug}): {change_type}")

    def log_agent_execution(
        self,
        stage_slug: str,
        stage_name: str,
        agent_name: str,
        execution_data: dict[str, Any],
    ) -> None:
        """
        Log agent execution within a stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            stage_name: Stage name (e.g., "Idea Refinement")
            agent_name: Name of the agent
            execution_data: Execution data (duration, tokens, status, etc.)
        """
        stage_dir = self._get_stage_dir(stage_slug)

        entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_slug=stage_slug,
            stage_name=stage_name,
            event_type="agent_execution",
            data={"agent_name": agent_name, **execution_data},
        )

        # Write to agent executions log
        executions_file = stage_dir / "agent_executions.jsonl"
        self._write_jsonl(executions_file, entry)

        logger.info(f"Agent execution logged: {agent_name} in stage '{stage_name}' ({stage_slug})")

    def write_session_summary(self, summary_data: dict[str, Any]) -> None:
        """
        Write session summary with aggregated metrics.

        Args:
            summary_data: Summary data (total_duration, total_tokens, total_cost, phases, etc.)
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            **summary_data,
        }

        summary_file = self.base_log_dir / "session_summary.json"
        self._write_json(summary_file, summary)

        logger.info("Session summary written")

    def get_stage_metrics(self, stage_slug: str) -> dict[str, Any] | None:
        """
        Get metrics for a specific stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")

        Returns:
            Stage metrics dictionary or None if not found
        """
        stage_dir = self._get_stage_dir(stage_slug)
        metrics_file = stage_dir / "metrics.json"

        if not metrics_file.exists():
            return None

        try:
            with open(metrics_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metrics from {metrics_file}: {e}")
            return None

    def get_session_summary(self) -> dict[str, Any] | None:
        """
        Get session summary.

        Returns:
            Session summary dictionary or None if not found
        """
        summary_file = self.base_log_dir / "session_summary.json"

        if not summary_file.exists():
            return None

        try:
            with open(summary_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read summary from {summary_file}: {e}")
            return None


# Global stage logger instance
_stage_logger: StageLogger | None = None


def get_stage_logger() -> StageLogger:
    """
    Get or create global stage logger instance.

    Returns:
        StageLogger instance
    """
    global _stage_logger

    if _stage_logger is None:
        _stage_logger = StageLogger()
        logger.info("Created global StageLogger instance")

    return _stage_logger


# Backward compatibility aliases
PhaseLogEntry = StageLogEntry
PhaseLogger = StageLogger
get_phase_logger = get_stage_logger
