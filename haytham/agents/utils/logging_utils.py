"""Logging utilities for Haytham agents."""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class LogEntry:
    """Structured log entry for agent interactions."""

    timestamp: str
    session_id: str
    agent_name: str
    interaction_type: str  # 'llm_input', 'llm_output', 'agent_call', 'agent_response', 'error'
    content: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class SessionManager:
    """
    Manages logging sessions for workflow executions.

    Each workflow execution gets a unique session ID and dedicated log directory.
    Sessions track start/end times and organize all logs chronologically.
    """

    def __init__(self, base_log_dir: str = "haytham/logs/sessions"):
        """
        Initialize session manager.

        Args:
            base_log_dir: Base directory for session logs
        """
        self.base_log_dir = Path(base_log_dir)
        self.current_session_id: str | None = None
        self.current_session_dir: Path | None = None
        self.session_start_time: datetime | None = None

        # Create base log directory if it doesn't exist
        self.base_log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"SessionManager initialized with base_log_dir: {self.base_log_dir}")

    def start_session(self) -> str:
        """
        Start a new logging session.

        Returns:
            Session ID (UUID)
        """
        # Generate unique session ID
        self.current_session_id = str(uuid.uuid4())
        self.session_start_time = datetime.now()

        # Create session directory
        self.current_session_dir = self.base_log_dir / self.current_session_id
        self.current_session_dir.mkdir(parents=True, exist_ok=True)

        # Create session metadata file
        metadata = {
            "session_id": self.current_session_id,
            "start_time": self.session_start_time.isoformat(),
            "status": "active",
        }

        metadata_file = self.current_session_dir / "session_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Started logging session: {self.current_session_id}")
        logger.info(f"Session logs directory: {self.current_session_dir}")

        return self.current_session_id

    def end_session(self, summary: dict[str, Any] | None = None) -> None:
        """
        End the current logging session.

        Args:
            summary: Optional summary data to include in session metadata
        """
        if not self.current_session_id:
            logger.warning("No active session to end")
            return

        session_end_time = datetime.now()
        duration = (session_end_time - self.session_start_time).total_seconds()

        # Update session metadata
        metadata_file = self.current_session_dir / "session_metadata.json"
        with open(metadata_file) as f:
            metadata = json.load(f)

        metadata.update(
            {
                "end_time": session_end_time.isoformat(),
                "duration_seconds": duration,
                "status": "completed",
            }
        )

        if summary:
            metadata["summary"] = summary

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Ended logging session: {self.current_session_id} (duration: {duration:.2f}s)")

        # Clear current session
        self.current_session_id = None
        self.current_session_dir = None
        self.session_start_time = None

    def get_session_id(self) -> str | None:
        """Get current session ID."""
        return self.current_session_id

    def get_session_dir(self) -> Path | None:
        """Get current session directory."""
        return self.current_session_dir


class AgentLogger:
    """
    Structured logger for agent interactions.

    Logs all LLM interactions, inter-agent communications, and errors
    with timestamps, agent names, and metadata.
    """

    def __init__(self, agent_name: str, session_manager: SessionManager):
        """
        Initialize agent logger.

        Args:
            agent_name: Name of the agent (e.g., 'ceo', 'market_intelligence')
            session_manager: Session manager instance
        """
        self.agent_name = agent_name
        self.session_manager = session_manager
        self.token_usage: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        logger.debug(f"AgentLogger initialized for agent: {agent_name}")

    def _write_log_entry(self, entry: LogEntry) -> None:
        """
        Write log entry to file.

        Args:
            entry: Log entry to write
        """
        session_dir = self.session_manager.get_session_dir()
        if not session_dir:
            logger.warning(f"No active session, skipping log entry for {self.agent_name}")
            return

        # Ensure session directory exists (in case it was deleted or not created)
        try:
            session_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create session directory {session_dir}: {e}")
            return

        # Create agent-specific log file
        log_file = session_dir / f"{self.agent_name}.log"

        # Format log entry with clear delimiters
        log_text = f"""
{"=" * 80}
TIMESTAMP: {entry.timestamp}
AGENT: {entry.agent_name}
TYPE: {entry.interaction_type}
{"=" * 80}

{entry.content}

METADATA:
{json.dumps(entry.metadata, indent=2)}

{"=" * 80}

"""

        # Append to log file
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_text)
        except Exception as e:
            logger.error(f"Failed to write log entry to {log_file}: {e}")

    def log_llm_input(self, prompt: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Log LLM input prompt.

        Args:
            prompt: Input prompt sent to LLM
            metadata: Optional metadata (model, temperature, etc.)
        """
        session_id = self.session_manager.get_session_id()
        if not session_id:
            logger.warning(f"No active session, skipping LLM input log for {self.agent_name}")
            return

        # Estimate tokens
        input_tokens = estimate_tokens(prompt)
        self.token_usage["input_tokens"] += input_tokens
        self.token_usage["total_tokens"] += input_tokens

        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            agent_name=self.agent_name,
            interaction_type="llm_input",
            content=prompt,
            metadata={**(metadata or {}), "estimated_tokens": input_tokens},
        )

        self._write_log_entry(entry)
        logger.info(f"[{self.agent_name}] LLM input logged ({input_tokens} tokens)")

    def log_llm_output(self, response: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Log LLM output response.

        Args:
            response: Output response from LLM
            metadata: Optional metadata (finish_reason, etc.)
        """
        session_id = self.session_manager.get_session_id()
        if not session_id:
            logger.warning(f"No active session, skipping LLM output log for {self.agent_name}")
            return

        # Estimate tokens
        output_tokens = estimate_tokens(response)
        self.token_usage["output_tokens"] += output_tokens
        self.token_usage["total_tokens"] += output_tokens

        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            agent_name=self.agent_name,
            interaction_type="llm_output",
            content=response,
            metadata={**(metadata or {}), "estimated_tokens": output_tokens},
        )

        self._write_log_entry(entry)
        logger.info(f"[{self.agent_name}] LLM output logged ({output_tokens} tokens)")

    def log_agent_call(
        self, target_agent: str, input_data: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Log inter-agent communication (calling another agent).

        Args:
            target_agent: Name of the agent being called
            input_data: Input data passed to the agent
            metadata: Optional metadata
        """
        session_id = self.session_manager.get_session_id()
        if not session_id:
            logger.warning(f"No active session, skipping agent call log for {self.agent_name}")
            return

        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            agent_name=self.agent_name,
            interaction_type="agent_call",
            content=f"Calling agent: {target_agent}\n\nInput:\n{input_data}",
            metadata={**(metadata or {}), "target_agent": target_agent},
        )

        self._write_log_entry(entry)
        logger.info(f"[{self.agent_name}] Agent call logged: {self.agent_name} -> {target_agent}")

    def log_agent_response(
        self, source_agent: str, response_data: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Log inter-agent communication (receiving response from another agent).

        Args:
            source_agent: Name of the agent that responded
            response_data: Response data received from the agent
            metadata: Optional metadata
        """
        session_id = self.session_manager.get_session_id()
        if not session_id:
            logger.warning(f"No active session, skipping agent response log for {self.agent_name}")
            return

        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            agent_name=self.agent_name,
            interaction_type="agent_response",
            content=f"Response from agent: {source_agent}\n\nResponse:\n{response_data}",
            metadata={**(metadata or {}), "source_agent": source_agent},
        )

        self._write_log_entry(entry)
        logger.info(
            f"[{self.agent_name}] Agent response logged: {source_agent} -> {self.agent_name}"
        )

    def log_error(
        self, error: Exception, context: str | None = None, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Log error with context.

        Args:
            error: Exception that occurred
            context: Optional context description
            metadata: Optional metadata
        """
        session_id = self.session_manager.get_session_id()
        if not session_id:
            logger.warning(f"No active session, skipping error log for {self.agent_name}")
            return

        # Format error content
        error_content = f"Error: {type(error).__name__}: {str(error)}"
        if context:
            error_content = f"Context: {context}\n\n{error_content}"

        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            agent_name=self.agent_name,
            interaction_type="error",
            content=error_content,
            metadata={**(metadata or {}), "error_type": type(error).__name__},
        )

        self._write_log_entry(entry)
        logger.error(f"[{self.agent_name}] Error logged: {type(error).__name__}")

    def get_token_usage(self) -> dict[str, int]:
        """
        Get token usage statistics for this agent.

        Returns:
            Dictionary with input_tokens, output_tokens, and total_tokens
        """
        return self.token_usage.copy()

    def write_token_summary(self) -> None:
        """Write token usage summary to session directory."""
        session_dir = self.session_manager.get_session_dir()
        if not session_dir:
            logger.warning(f"No active session, skipping token summary for {self.agent_name}")
            return

        # Ensure session directory exists
        try:
            session_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create session directory {session_dir}: {e}")
            return

        summary_file = session_dir / f"{self.agent_name}_token_summary.json"
        summary_data = {
            "agent_name": self.agent_name,
            "timestamp": datetime.now().isoformat(),
            **self.token_usage,
        }

        try:
            with open(summary_file, "w") as f:
                json.dump(summary_data, f, indent=2)
            logger.info(
                f"[{self.agent_name}] Token summary written: {self.token_usage['total_tokens']} total tokens"
            )
        except Exception as e:
            logger.error(f"Failed to write token summary to {summary_file}: {e}")


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses a simple heuristic: ~4 characters per token (average for English text).
    This is an approximation - actual token counts may vary by model and tokenizer.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Simple heuristic: 4 characters per token on average
    # This is a rough approximation but works well enough for tracking
    return len(text) // 4


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """
    Get or create global session manager instance.

    Returns:
        SessionManager instance
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager()
        logger.info("Created global SessionManager instance")

    return _session_manager


def create_agent_logger(agent_name: str) -> AgentLogger:
    """
    Create an agent logger for the specified agent.

    Args:
        agent_name: Name of the agent

    Returns:
        AgentLogger instance
    """
    session_manager = get_session_manager()
    return AgentLogger(agent_name, session_manager)
