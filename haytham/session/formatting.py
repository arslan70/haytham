"""Shared markdown formatting for session persistence.

Pure functions that generate markdown content for checkpoints, agent outputs,
user feedback, and manifest files. Used by ``SessionManager`` to separate
formatting concerns from session lifecycle management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def format_agent_output(
    *,
    agent_name: str,
    context_label: str,
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
    """Format agent output as markdown.

    Args:
        agent_name: Name of the agent that produced the output.
        context_label: Human-readable label for where this ran
            (e.g. ``"idea-analysis - Idea Analysis"`` or ``"2 - Market Context"``).
        executed: ISO-8601 timestamp of execution.
        duration: Wall-clock seconds (``None`` if unknown).
        status: Completion status (``"completed"``, ``"failed"``, etc.).
        model: Model ID used, or ``None``.
        input_tokens: Input token count, or ``None``.
        output_tokens: Output token count, or ``None``.
        tools_used: List of tool names invoked during execution.
        output_content: The agent's primary output text.
        error_type: Exception class name on failure, or ``None``.
        error_message: Error description on failure, or ``None``.
        stack_trace: Full traceback on failure, or ``None``.
    """
    duration_str = f"{duration:.1f}s" if duration is not None else "-"
    model_str = model if model else "-"
    input_tokens_str = str(input_tokens) if input_tokens is not None else "-"
    output_tokens_str = str(output_tokens) if output_tokens is not None else "-"
    tools_str = ", ".join(tools_used) if tools_used else "none"

    content = f"""# Agent Output: {agent_name}

## Metadata
- Agent: {agent_name}
- Context: {context_label}
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


def format_user_feedback(
    *,
    context_name: str,
    reviewed: bool,
    approved: bool,
    timestamp: str,
    comments: str,
    requested_changes: list[str],
    action: str,
    retry_count: int,
) -> str:
    """Format user feedback as markdown.

    Args:
        context_name: Display name of the stage or phase.
        reviewed: Whether the output was reviewed.
        approved: Whether the output was approved.
        timestamp: ISO-8601 timestamp of the feedback.
        comments: Free-text user comments.
        requested_changes: List of requested change descriptions.
        action: Action taken (e.g. ``"approve"``, ``"retry"``).
        retry_count: Number of retries so far.
    """
    content = f"""# User Feedback: {context_name}

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


def format_checkpoint(
    *,
    stage_slug: str,
    stage_name: str,
    status: str,
    started: str | None,
    completed: str | None,
    duration: float | None,
    retry_count: int,
    execution_mode: str,
    agents: list[dict[str, Any]],
    errors: list[str],
    prev_stage_name: str,
    next_stage_slug: str,
    next_stage_name: str,
) -> str:
    """Format checkpoint.md content for a stage.

    All stage navigation data (previous/next stage) is passed explicitly
    so this function stays independent of the stage registry.

    Args:
        stage_slug: The slug identifier for this stage.
        stage_name: Human-readable display name for this stage.
        status: Current stage status (e.g. ``"completed"``, ``"failed"``).
        started: ISO-8601 timestamp when the stage started, or ``None``.
        completed: ISO-8601 timestamp when the stage completed, or ``None``.
        duration: Wall-clock seconds, or ``None``.
        retry_count: Number of retry attempts.
        execution_mode: Execution mode (``"single"``, ``"parallel"``, etc.).
        agents: List of agent execution detail dicts.
        errors: List of error message strings.
        prev_stage_name: Display name of the previous stage, or ``"None"``.
        next_stage_slug: Slug of the next stage, or ``"-"``.
        next_stage_name: Display name of the next stage, or ``"None"``.
    """
    started_str = started if started else "-"
    completed_str = completed if completed else "-"
    duration_str = f"{duration:.1f}s" if duration is not None else "-"

    content = f"""# Stage Checkpoint: {stage_name}

## Metadata
- Stage: {stage_slug}
- Stage Name: {stage_name}
- Status: {status}
- Started: {started_str}
- Completed: {completed_str}
- Duration: {duration_str}
- Retry Count: {retry_count}
- Execution Mode: {execution_mode}

## Agents in Stage
"""

    for agent in agents:
        agent_name = agent.get("agent_name", "unknown")
        agent_status = agent.get("status", "unknown")
        content += f"- {agent_name}: {agent_status}\n"

    outputs = ", ".join([a.get("output_file", "") for a in agents])
    total_tokens = sum(a.get("tokens") or 0 for a in agents)
    input_tokens = sum(a.get("input_tokens") or 0 for a in agents)
    output_tokens = sum(a.get("output_tokens") or 0 for a in agents)
    cost = sum(a.get("cost") or 0.0 for a in agents)
    execution_times = ", ".join(
        [f"{a.get('agent_name', 'unknown')}: {a.get('duration') or 0:.1f}s" for a in agents]
    )

    ready = "true" if status == "completed" else "false"
    blocking = "none" if not errors else ", ".join(errors)

    content += f"""
## Inputs
- Previous Stage: {prev_stage_name}
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

## Next Stage
- Stage: {next_stage_slug}
- Stage Name: {next_stage_name}
- Ready to Execute: {ready}
- Blocking Issues: {blocking}
"""

    if errors:
        content += "\n## Errors\n"
        for error in errors:
            content += f"- {error}\n"

    return content


def create_manifest(
    *,
    stages: list[tuple[str, str]],
    created: str,
    system_goal: str | None,
) -> str:
    """Create initial session_manifest.md content.

    Returns the manifest content as a string. The caller is responsible
    for writing it to disk.

    Args:
        stages: List of ``(slug, display_name)`` tuples for all stages.
        created: ISO-8601 timestamp.
        system_goal: The system goal string, or ``None`` if not set yet.
    """
    system_goal_display = system_goal if system_goal else "(awaiting user input)"

    stage_rows = []
    for slug, display_name in stages:
        stage_rows.append(f"| {slug} | {display_name} | pending | - | - | - |")
    stage_table = "\n".join(stage_rows)

    return f"""# Session Manifest

## Metadata
- Created: {created}
- Last Updated: {created}
- Status: in_progress
- System Goal: {system_goal_display}

## Stage Status

| Stage | Name | Status | Started | Completed | Duration |
|-------|------|--------|---------|-----------|----------|
{stage_table}

## Current Stage
- Stage: (none)
- Name: Not Started
- Status: pending
- Progress: 0 of {len(stages)}

## Metrics
- Total Duration: 0s
- Total Tokens: 0
- Total Cost: $0.00
"""


def update_manifest(
    *,
    manifest_content: str,
    stage_slug: str,
    stage_display_name: str,
    status: str,
    started: str | None,
    completed: str | None,
    duration: float | None,
    total_stages: int,
    stages_list: list[tuple[str, str]],
) -> str:
    """Update session_manifest.md content with a stage status change.

    Returns the updated manifest content as a string. The caller is
    responsible for reading and writing the file.

    Args:
        manifest_content: Current manifest file content.
        stage_slug: Slug of the stage to update.
        stage_display_name: Display name of the stage (looked up by caller).
        status: New status for the stage.
        started: ISO-8601 timestamp when started, or ``None``.
        completed: ISO-8601 timestamp when completed, or ``None``.
        duration: Duration in seconds, or ``None``.
        total_stages: Total number of stages in the workflow.
        stages_list: List of ``(slug, display_name)`` tuples for computing
            progress (how many stages are completed).
    """
    lines = manifest_content.split("\n")

    # Update stage status table
    started_str = started if started else "-"
    completed_str = completed if completed else "-"
    duration_str = f"{int(duration)}s" if duration else "-"

    # Find and update the stage row, or add it if not found
    new_row = (
        f"| {stage_slug} | {stage_display_name} | {status} | "
        f"{started_str} | {completed_str} | {duration_str} |"
    )
    row_found = False
    for i, line in enumerate(lines):
        if line.startswith(f"| {stage_slug} |"):
            lines[i] = new_row
            row_found = True
            break

    # If stage row not found, insert it before the empty line after the table
    if not row_found:
        for i, line in enumerate(lines):
            # Find the end of the stage status table (empty line or next section)
            if line.startswith("| ") and "|" in line[2:]:
                continue
            elif i > 0 and lines[i - 1].startswith("| "):
                # Insert new row here (after last table row)
                lines.insert(i, new_row)
                break

    # Calculate progress (number of completed stages)
    completed_count = 0
    for slug, _display_name in stages_list:
        for line in lines:
            if line.startswith(f"| {slug} |") and "| completed |" in line:
                completed_count += 1
                break

    # Update current stage section
    for i, line in enumerate(lines):
        if line.startswith("- Stage:") and i > 0:
            # Check if this is in the Current Stage section
            if any("Current Stage" in lines[j] for j in range(max(0, i - 5), i)):
                lines[i] = f"- Stage: {stage_slug}"
        elif line.startswith("- Name:") and i > 0:
            if any("Current Stage" in lines[j] for j in range(max(0, i - 5), i)):
                lines[i] = f"- Name: {stage_display_name}"
        elif line.startswith("- Status:") and i > 0:
            if any("Current Stage" in lines[j] for j in range(max(0, i - 5), i)):
                lines[i] = f"- Status: {status}"
        elif line.startswith("- Progress:"):
            lines[i] = f"- Progress: {completed_count} of {total_stages}"

    # Update last updated timestamp
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for i, line in enumerate(lines):
        if line.startswith("- Last Updated:"):
            lines[i] = f"- Last Updated: {now}"
            break

    return "\n".join(lines)


def parse_manifest(
    content: str,
    *,
    valid_stage_slugs: set[str],
) -> dict[str, Any]:
    """Parse session_manifest.md content into a structured dict.

    Args:
        content: Raw manifest file content.
        valid_stage_slugs: Set of valid stage slugs for filtering table rows.

    Returns:
        Dict with keys: ``created``, ``last_updated``, ``status``,
        ``system_goal``, ``current_stage``, ``completed_stages``,
        ``stage_statuses``.
    """
    lines = content.split("\n")
    session_state: dict[str, Any] = {
        "created": None,
        "last_updated": None,
        "status": None,
        "system_goal": None,
        "current_stage": None,
        "completed_stages": [],
        "stage_statuses": {},
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
            if line.startswith("- Created:"):
                session_state["created"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Last Updated:"):
                session_state["last_updated"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Status:"):
                session_state["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("- System Goal:"):
                goal = line.split(":", 1)[1].strip()
                # Handle "(awaiting user input)" as None
                if goal != "(awaiting user input)":
                    session_state["system_goal"] = goal

    # Parse stage status table
    in_table = False
    for line in lines:
        if line.startswith("| Stage | Name |"):
            in_table = True
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1]:
                stage_slug = parts[1]
                stage_status = parts[3]

                # Validate it's a real stage slug
                if stage_slug in valid_stage_slugs:
                    session_state["stage_statuses"][stage_slug] = stage_status

                    if stage_status == "completed":
                        session_state["completed_stages"].append(stage_slug)
        elif in_table and not line.startswith("|"):
            break

    # Parse current stage
    in_current_stage = False
    for line in lines:
        if line.strip() == "## Current Stage":
            in_current_stage = True
            continue
        elif line.startswith("## ") and in_current_stage:
            in_current_stage = False

        if in_current_stage:
            if line.startswith("- Stage:"):
                stage_value = line.split(":", 1)[1].strip()
                if stage_value and stage_value != "(none)":
                    session_state["current_stage"] = stage_value

    return session_state
