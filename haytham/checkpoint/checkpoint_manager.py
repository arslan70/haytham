"""Checkpoint management for phased workflow execution.

This module provides checkpoint persistence, session resume, and recovery
for the phased workflow architecture.
"""

from datetime import datetime
from pathlib import Path
from typing import Any


class CheckpointManager:
    """Manages checkpoints, session state, and phase outputs for phased workflows.

    The CheckpointManager handles:
    - Session creation and manifest management
    - Phase checkpoint saving and loading
    - Agent output persistence
    - Session resume and recovery
    - Schema validation

    Directory Structure:
        projects/{project_id}/sessions/{session_id}/
        ├── session_manifest.md          # Session metadata and phase status
        ├── phase_1_concept/
        │   ├── checkpoint.md            # Phase metadata
        │   ├── concept_expansion.md     # Agent output
        │   └── user_feedback.md         # User review
        ├── phase_2_market_research/
        │   ├── checkpoint.md
        │   ├── market_intelligence.md
        │   ├── competitor_analysis.md
        │   └── user_feedback.md
        └── ...
    """

    # Phase name mappings
    PHASE_NAMES = {
        1: "Concept Expansion",
        2: "Market Research",
        3: "Niche Selection",
        4: "Product Strategy",
        5: "Business Planning",
        6: "Validation",
        7: "Final Synthesis",
    }

    PHASE_DIRS = {
        1: "phase_1_concept",
        2: "phase_2_market_research",
        3: "phase_3_niche_selection",
        4: "phase_4_product_strategy",
        5: "phase_5_business_planning",
        6: "phase_6_validation",
        7: "phase_7_synthesis",
    }

    def __init__(self, base_dir: str = "projects"):
        """Initialize the CheckpointManager.

        Args:
            base_dir: Base directory for all projects (default: "projects")
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        project_id: str,
        session_id: str,
        user_id: str,
        workflow_type: str = "idea_validation",
        execution_mode: str = "mvp",
    ) -> Path:
        """Create a new session directory structure.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            user_id: The user identifier
            workflow_type: Type of workflow (default: "idea_validation")
            execution_mode: "mvp" or "full" (default: "mvp")

        Returns:
            Path to the session directory

        Raises:
            ValueError: If execution_mode is not "mvp" or "full"
        """
        if execution_mode not in ["mvp", "full"]:
            raise ValueError(f"execution_mode must be 'mvp' or 'full', got: {execution_mode}")

        # Create session directory
        session_dir = self.base_dir / project_id / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create phase directories based on execution mode
        phases_to_create = [1, 2, 3, 6, 7]  # MVP mode phases
        if execution_mode == "full":
            phases_to_create = [1, 2, 3, 4, 5, 6, 7]  # All phases

        for phase_num in phases_to_create:
            phase_dir = session_dir / self.PHASE_DIRS[phase_num]
            phase_dir.mkdir(exist_ok=True)

        # Create session manifest
        self._create_session_manifest(
            session_dir, session_id, project_id, user_id, workflow_type, execution_mode
        )

        return session_dir

    def save_checkpoint(
        self,
        project_id: str,
        session_id: str,
        phase_num: int,
        status: str,
        agents: list[dict[str, Any]],
        started: str | None = None,
        completed: str | None = None,
        duration: float | None = None,
        retry_count: int = 0,
        execution_mode: str = "single",
        errors: list[str] | None = None,
    ) -> None:
        """Save a phase checkpoint.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            phase_num: Phase number (1-7)
            status: Phase status (pending, in_progress, completed, failed, skipped)
            agents: List of agent execution details
            started: ISO 8601 timestamp when phase started
            completed: ISO 8601 timestamp when phase completed
            duration: Phase duration in seconds
            retry_count: Number of retry attempts
            execution_mode: Execution mode (single, parallel, sequential_interactive)
            errors: List of error messages (if any)

        Raises:
            ValueError: If phase_num is not 1-7 or status is invalid
            FileNotFoundError: If session directory does not exist
        """
        if phase_num not in range(1, 8):
            raise ValueError(f"phase_num must be 1-7, got: {phase_num}")

        valid_statuses = [
            "pending",
            "in_progress",
            "completed",
            "failed",
            "skipped",
            "requires_retry",
        ]
        if status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got: {status}")

        session_dir = self.base_dir / project_id / "sessions" / session_id
        if not session_dir.exists():
            raise FileNotFoundError(f"Session directory not found: {session_dir}")

        phase_dir = session_dir / self.PHASE_DIRS[phase_num]
        phase_dir.mkdir(exist_ok=True)

        # Create checkpoint content
        checkpoint_content = self._format_checkpoint(
            phase_num=phase_num,
            phase_name=self.PHASE_NAMES[phase_num],
            status=status,
            started=started,
            completed=completed,
            duration=duration,
            retry_count=retry_count,
            execution_mode=execution_mode,
            agents=agents,
            errors=errors or [],
        )

        # Write checkpoint file
        checkpoint_path = phase_dir / "checkpoint.md"
        checkpoint_path.write_text(checkpoint_content)

        # Update session manifest
        self._update_session_manifest(session_dir, phase_num, status, started, completed, duration)

    def save_agent_output(
        self,
        project_id: str,
        session_id: str,
        phase_num: int,
        agent_name: str,
        output_content: str,
        status: str = "completed",
        duration: float | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        tools_used: list[str] | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        stack_trace: str | None = None,
    ) -> None:
        """Save agent output to a markdown file.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            phase_num: Phase number (1-7)
            agent_name: Name of the agent
            output_content: The agent's output content
            status: Agent status (completed, failed)
            duration: Execution duration in seconds
            model: Model identifier used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            tools_used: List of tools used by the agent
            error_type: Error type (if failed)
            error_message: Error message (if failed)
            stack_trace: Stack trace (if failed)

        Raises:
            FileNotFoundError: If phase directory does not exist
        """
        session_dir = self.base_dir / project_id / "sessions" / session_id
        phase_dir = session_dir / self.PHASE_DIRS[phase_num]

        if not phase_dir.exists():
            raise FileNotFoundError(f"Phase directory not found: {phase_dir}")

        # Create agent output content
        now = datetime.utcnow().isoformat() + "Z"
        agent_output = self._format_agent_output(
            agent_name=agent_name,
            phase_num=phase_num,
            phase_name=self.PHASE_NAMES[phase_num],
            executed=now,
            duration=duration,
            status=status,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tools_used=tools_used or [],
            output_content=output_content,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
        )

        # Write agent output file
        output_path = phase_dir / f"{agent_name}.md"
        output_path.write_text(agent_output)

    def save_user_feedback(
        self,
        project_id: str,
        session_id: str,
        phase_num: int,
        reviewed: bool,
        approved: bool,
        comments: str = "",
        requested_changes: list[str] | None = None,
        action: str = "approved",
        retry_count: int = 0,
    ) -> None:
        """Save user feedback for a phase.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            phase_num: Phase number (1-7)
            reviewed: Whether the phase was reviewed
            approved: Whether the phase was approved
            comments: User comments
            requested_changes: List of requested changes
            action: Action taken (approved, retry_with_changes, skip_phase)
            retry_count: Number of retries

        Raises:
            FileNotFoundError: If phase directory does not exist
        """
        session_dir = self.base_dir / project_id / "sessions" / session_id
        phase_dir = session_dir / self.PHASE_DIRS[phase_num]

        if not phase_dir.exists():
            raise FileNotFoundError(f"Phase directory not found: {phase_dir}")

        # Create user feedback content
        now = datetime.utcnow().isoformat() + "Z"
        feedback_content = self._format_user_feedback(
            phase_name=self.PHASE_NAMES[phase_num],
            reviewed=reviewed,
            approved=approved,
            timestamp=now,
            comments=comments,
            requested_changes=requested_changes or [],
            action=action,
            retry_count=retry_count,
        )

        # Write user feedback file
        feedback_path = phase_dir / "user_feedback.md"
        feedback_path.write_text(feedback_content)

    def load_session(self, project_id: str, session_id: str) -> dict[str, Any]:
        """Load session state from session_manifest.md.

        Args:
            project_id: The project identifier
            session_id: The session identifier

        Returns:
            Dict containing session state including current phase and status

        Raises:
            FileNotFoundError: If session manifest does not exist
        """
        session_dir = self.base_dir / project_id / "sessions" / session_id
        manifest_path = session_dir / "session_manifest.md"

        if not manifest_path.exists():
            raise FileNotFoundError(f"Session manifest not found: {manifest_path}")

        # Parse session manifest
        manifest_content = manifest_path.read_text()
        session_state = self._parse_session_manifest(manifest_content)

        return session_state

    def get_phase_outputs(
        self, project_id: str, session_id: str, phase_nums: list[int] | None = None
    ) -> dict[int, dict[str, str]]:
        """Load agent outputs from specified phases.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            phase_nums: List of phase numbers to load (None = all completed phases)

        Returns:
            Dict mapping phase_num to dict of agent_name -> output_content

        Raises:
            FileNotFoundError: If session directory does not exist
        """
        session_dir = self.base_dir / project_id / "sessions" / session_id

        if not session_dir.exists():
            raise FileNotFoundError(f"Session directory not found: {session_dir}")

        # If no phase_nums specified, load all completed phases
        if phase_nums is None:
            session_state = self.load_session(project_id, session_id)
            phase_nums = session_state.get("completed_phases", [])

        outputs = {}

        for phase_num in phase_nums:
            phase_dir = session_dir / self.PHASE_DIRS[phase_num]

            if not phase_dir.exists():
                continue

            phase_outputs = {}

            # Load all .md files except checkpoint.md and user_feedback.md
            for output_file in phase_dir.glob("*.md"):
                if output_file.name in ["checkpoint.md", "user_feedback.md"]:
                    continue

                agent_name = output_file.stem
                content = output_file.read_text()

                # Extract just the output content (skip metadata)
                output_content = self._extract_output_content(content)
                phase_outputs[agent_name] = output_content

            if phase_outputs:
                outputs[phase_num] = phase_outputs

        return outputs

    def get_approved_phases(self, project_id: str, session_id: str) -> list[int]:
        """Get list of phases that have been approved by the user.

        A phase is considered approved if:
        1. It has a phase directory
        2. It has a user_feedback.md file
        3. The feedback file shows Approved: true

        Args:
            project_id: The project identifier
            session_id: The session identifier

        Returns:
            List of approved phase numbers in ascending order
        """
        session_dir = self.base_dir / project_id / "sessions" / session_id

        if not session_dir.exists():
            return []

        approved_phases = []

        # Check each phase directory
        for phase_num, phase_dir_name in self.PHASE_DIRS.items():
            phase_dir = session_dir / phase_dir_name
            feedback_file = phase_dir / "user_feedback.md"

            # Check if directory and feedback file exist
            if phase_dir.exists() and feedback_file.exists():
                # Parse feedback file to check if actually approved
                try:
                    feedback_content = feedback_file.read_text()
                    # Look for "- Approved: true" line
                    if "- Approved: true" in feedback_content:
                        approved_phases.append(phase_num)
                except Exception as e:
                    # If we can't read the file, don't count it as approved
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to read feedback file for phase {phase_num}: {e}")

        return sorted(approved_phases)

    def validate_checkpoint(
        self, project_id: str, session_id: str, phase_num: int
    ) -> tuple[bool, list[str]]:
        """Validate a phase checkpoint.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            phase_num: Phase number (1-7)

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        session_dir = self.base_dir / project_id / "sessions" / session_id
        phase_dir = session_dir / self.PHASE_DIRS[phase_num]
        checkpoint_path = phase_dir / "checkpoint.md"

        errors = []

        # Check if checkpoint exists
        if not checkpoint_path.exists():
            errors.append(f"Checkpoint file not found: {checkpoint_path}")
            return False, errors

        # Read checkpoint content
        try:
            content = checkpoint_path.read_text()
        except Exception as e:
            errors.append(f"Failed to read checkpoint: {e}")
            return False, errors

        # Validate required sections
        required_sections = [
            "# Phase Checkpoint:",
            "## Metadata",
            "## Agents in Phase",
            "## Inputs",
            "## Outputs",
            "## Metrics",
        ]

        for section in required_sections:
            if section not in content:
                errors.append(f"Missing required section: {section}")

        # Validate metadata fields
        required_fields = ["Phase Number:", "Phase Name:", "Status:", "Started:"]

        for field in required_fields:
            if field not in content:
                errors.append(f"Missing required field: {field}")

        return len(errors) == 0, errors

    # Private helper methods

    def _create_session_manifest(
        self,
        session_dir: Path,
        session_id: str,
        project_id: str,
        user_id: str,
        workflow_type: str,
        execution_mode: str,
    ) -> None:
        """Create initial session_manifest.md."""
        now = datetime.utcnow().isoformat() + "Z"

        content = f"""# Session Manifest

## Metadata
- Session ID: {session_id}
- Project ID: {project_id}
- User ID: {user_id}
- Workflow Type: {workflow_type}
- Execution Mode: {execution_mode}
- Created: {now}
- Last Updated: {now}
- Status: in_progress

## Phase Status

| Phase | Name | Status | Started | Completed | Duration |
|-------|------|--------|---------|-----------|----------|
| 1 | Concept Expansion | pending | - | - | - |
| 2 | Market Research | pending | - | - | - |
| 3 | Niche Selection | pending | - | - | - |
"""

        if execution_mode == "full":
            content += """| 4 | Product Strategy | pending | - | - | - |
| 5 | Business Planning | pending | - | - | - |
"""

        content += """| 6 | Validation | pending | - | - | - |
| 7 | Final Synthesis | pending | - | - | - |

## Current Phase
- Phase: 0
- Name: Not Started
- Status: pending
- Can Resume: false

## Metrics
- Total Duration: 0s
- Total Tokens: 0
- Total Cost: $0.00
"""

        manifest_path = session_dir / "session_manifest.md"
        manifest_path.write_text(content)

    def _update_session_manifest(
        self,
        session_dir: Path,
        phase_num: int,
        status: str,
        started: str | None,
        completed: str | None,
        duration: float | None,
    ) -> None:
        """Update session_manifest.md with phase status."""
        manifest_path = session_dir / "session_manifest.md"

        if not manifest_path.exists():
            return

        content = manifest_path.read_text()
        lines = content.split("\n")

        # Update phase status table
        phase_name = self.PHASE_NAMES[phase_num]
        started_str = started if started else "-"
        completed_str = completed if completed else "-"
        duration_str = f"{int(duration)}s" if duration else "-"

        # Find and update the phase row
        for i, line in enumerate(lines):
            if line.startswith(f"| {phase_num} |"):
                lines[i] = (
                    f"| {phase_num} | {phase_name} | {status} | {started_str} | {completed_str} | {duration_str} |"
                )
                break

        # Update current phase section
        # Update for all statuses, not just "in_progress"
        for i, line in enumerate(lines):
            if (
                line.startswith("- Phase:")
                and i > 0
                and any("Current Phase" in lines[j] for j in range(max(0, i - 5), i))
            ):
                lines[i] = f"- Phase: {phase_num}"
            elif (
                line.startswith("- Name:")
                and i > 0
                and any("Current Phase" in lines[j] for j in range(max(0, i - 5), i))
            ):
                lines[i] = f"- Name: {phase_name}"
            elif (
                line.startswith("- Status:")
                and i > 0
                and any("Current Phase" in lines[j] for j in range(max(0, i - 5), i))
            ):
                lines[i] = f"- Status: {status}"
            elif line.startswith("- Can Resume:"):
                # Can resume if status is in_progress or failed
                can_resume = status in ["in_progress", "failed"]
                lines[i] = f"- Can Resume: {str(can_resume).lower()}"

        # Update last updated timestamp
        now = datetime.utcnow().isoformat() + "Z"
        for i, line in enumerate(lines):
            if line.startswith("- Last Updated:"):
                lines[i] = f"- Last Updated: {now}"
                break

        # Write updated content
        manifest_path.write_text("\n".join(lines))

    def _format_checkpoint(
        self,
        phase_num: int,
        phase_name: str,
        status: str,
        started: str | None,
        completed: str | None,
        duration: float | None,
        retry_count: int,
        execution_mode: str,
        agents: list[dict[str, Any]],
        errors: list[str],
    ) -> str:
        """Format checkpoint.md content."""
        started_str = started if started else "-"
        completed_str = completed if completed else "-"
        duration_str = f"{duration:.1f}s" if duration else "-"

        content = f"""# Phase Checkpoint: {phase_name}

## Metadata
- Phase Number: {phase_num}
- Phase Name: {phase_name}
- Status: {status}
- Started: {started_str}
- Completed: {completed_str}
- Duration: {duration_str}
- Retry Count: {retry_count}
- Execution Mode: {execution_mode}

## Agents in Phase
"""

        for agent in agents:
            agent_name = agent.get("agent_name", "unknown")
            agent_status = agent.get("status", "unknown")
            content += f"- {agent_name}: {agent_status}\n"

        content += """
## Inputs
- Previous Phase: {prev_phase}
- Required Context: []
- User Parameters: {{}}

## Outputs
- Agent Outputs: [{outputs}]
- User Feedback: user_feedback.md

## Metrics
- Total Tokens: {total_tokens}
- Input Tokens: {input_tokens}
- Output Tokens: {output_tokens}
- Cost: ${cost:.4f}
- Agent Execution Times: {execution_times}

## Next Phase
- Phase Number: {next_phase}
- Phase Name: {next_phase_name}
- Ready to Execute: {ready}
- Blocking Issues: {blocking}
""".format(
            prev_phase=self.PHASE_NAMES.get(phase_num - 1, "None"),
            outputs=", ".join([a.get("output_file", "") for a in agents]),
            total_tokens=sum(a.get("tokens") or 0 for a in agents),
            input_tokens=sum(a.get("input_tokens") or 0 for a in agents),
            output_tokens=sum(a.get("output_tokens") or 0 for a in agents),
            cost=sum(a.get("cost") or 0.0 for a in agents),
            execution_times=", ".join(
                [f"{a.get('agent_name', 'unknown')}: {a.get('duration') or 0:.1f}s" for a in agents]
            ),
            next_phase=phase_num + 1 if phase_num < 7 else "-",
            next_phase_name=self.PHASE_NAMES.get(phase_num + 1, "None"),
            ready="true" if status == "completed" else "false",
            blocking="none" if not errors else ", ".join(errors),
        )

        if errors:
            content += "\n## Errors\n"
            for error in errors:
                content += f"- {error}\n"

        return content

    def _format_agent_output(
        self,
        agent_name: str,
        phase_num: int,
        phase_name: str,
        executed: str,
        duration: float | None,
        status: str,
        model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        tools_used: list[str],
        output_content: str,
        error_type: str | None,
        error_message: str | None,
        stack_trace: str | None,
    ) -> str:
        """Format agent output markdown content."""
        duration_str = f"{duration:.1f}s" if duration else "-"
        model_str = model if model else "-"
        input_tokens_str = str(input_tokens) if input_tokens else "-"
        output_tokens_str = str(output_tokens) if output_tokens else "-"
        tools_str = ", ".join(tools_used) if tools_used else "none"

        content = f"""# Agent Output: {agent_name}

## Metadata
- Agent: {agent_name}
- Phase: {phase_num} - {phase_name}
- Executed: {executed}
- Duration: {duration_str}
- Status: {status}

## Execution Details
- Model: {model_str}
- Input Tokens: {input_tokens_str}
- Output Tokens: {output_tokens_str}
- Tools Used: [{tools_str}]

## Output

{output_content}
"""

        if status == "failed" and (error_type or error_message):
            content += f"""
## Error Details
- Error Type: {error_type if error_type else "Unknown"}
- Error Message: {error_message if error_message else "No message"}
"""
            if stack_trace:
                content += f"- Stack Trace:\n```\n{stack_trace}\n```\n"

        return content

    def _format_user_feedback(
        self,
        phase_name: str,
        reviewed: bool,
        approved: bool,
        timestamp: str,
        comments: str,
        requested_changes: list[str],
        action: str,
        retry_count: int,
    ) -> str:
        """Format user_feedback.md content."""
        content = f"""# User Feedback: {phase_name}

## Review Status
- Reviewed: {str(reviewed).lower()}
- Approved: {str(approved).lower()}
- Timestamp: {timestamp}

## User Comments
{comments if comments else "No comments provided"}

## Requested Changes
"""

        if requested_changes:
            for i, change in enumerate(requested_changes, 1):
                content += f"- Change {i}: {change}\n"
        else:
            content += "- No changes requested\n"

        content += f"""
## Action Taken
- Action: {action}
- Retry Count: {retry_count}
"""

        return content

    def _parse_session_manifest(self, content: str) -> dict[str, Any]:
        """Parse session_manifest.md content."""
        lines = content.split("\n")
        session_state = {
            "session_id": None,
            "project_id": None,
            "user_id": None,
            "workflow_type": None,
            "execution_mode": None,
            "created": None,
            "last_updated": None,
            "status": None,
            "current_phase": 0,
            "completed_phases": [],
            "phase_statuses": {},
        }

        # Parse metadata section
        in_metadata = False
        for line in lines:
            if line.strip() == "## Metadata":
                in_metadata = True
                continue
            elif line.startswith("## ") and in_metadata:
                in_metadata = False

            if in_metadata:
                if line.startswith("- Session ID:"):
                    session_state["session_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("- Project ID:"):
                    session_state["project_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("- User ID:"):
                    session_state["user_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("- Workflow Type:"):
                    session_state["workflow_type"] = line.split(":", 1)[1].strip()
                elif line.startswith("- Execution Mode:"):
                    session_state["execution_mode"] = line.split(":", 1)[1].strip()
                elif line.startswith("- Created:"):
                    session_state["created"] = line.split(":", 1)[1].strip()
                elif line.startswith("- Last Updated:"):
                    session_state["last_updated"] = line.split(":", 1)[1].strip()
                elif line.startswith("- Status:"):
                    session_state["status"] = line.split(":", 1)[1].strip()

        # Parse phase status table
        in_table = False
        for line in lines:
            if line.startswith("| Phase | Name |"):
                in_table = True
                continue
            if in_table and line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4 and parts[1].isdigit():
                    phase_num = int(parts[1])
                    phase_status = parts[3]
                    session_state["phase_statuses"][phase_num] = phase_status

                    if phase_status == "completed":
                        session_state["completed_phases"].append(phase_num)
            elif in_table and not line.startswith("|"):
                break

        # Parse current phase
        in_current_phase = False
        for line in lines:
            if line.strip() == "## Current Phase":
                in_current_phase = True
                continue
            elif line.startswith("## ") and in_current_phase:
                in_current_phase = False

            if in_current_phase:
                if line.startswith("- Phase:"):
                    try:
                        phase_value = line.split(":", 1)[1].strip()
                        if phase_value.isdigit():
                            session_state["current_phase"] = int(phase_value)
                    except (ValueError, IndexError):
                        pass

        return session_state

    def _extract_output_content(self, full_content: str) -> str:
        """Extract just the output content from agent output file."""
        # Find the "## Output" section
        if "## Output" not in full_content:
            return full_content

        # Extract content after "## Output"
        parts = full_content.split("## Output", 1)
        if len(parts) < 2:
            return full_content

        output_section = parts[1]

        # Check if output contains a raw SwarmResult string (from old buggy saves)
        # If so, try to extract the actual text from it
        if "SwarmResult(" in output_section and "'text':" in output_section:
            import re

            # Extract text content from the SwarmResult string representation
            # Pattern: 'text': 'actual content here'
            text_matches = re.findall(r"'text':\s*'([^']*(?:''[^']*)*)'", output_section)
            if text_matches:
                # Join all text blocks and unescape
                extracted_text = "\n\n".join(text_matches)
                # Unescape common escape sequences
                extracted_text = extracted_text.replace("\\n", "\n")
                extracted_text = extracted_text.replace("\\t", "\t")
                extracted_text = extracted_text.replace("\\'", "'")
                return extracted_text.strip()

        # Remove any subsequent metadata sections (## Error Details, etc.)
        # Only break on KNOWN metadata sections, not content sections
        known_metadata_sections = [
            "## Error Details",
            "## Metadata",
            "## Execution Details",
            "## Debug Info",
            "## Stack Trace",
        ]

        lines = output_section.split("\n")
        result_lines = []
        for line in lines:
            # Check if this line starts a known metadata section
            line_stripped = line.strip()
            if any(line_stripped.startswith(section) for section in known_metadata_sections):
                # This is a metadata section, stop here
                break
            result_lines.append(line)

        output_section = "\n".join(result_lines)

        return output_section.strip()
