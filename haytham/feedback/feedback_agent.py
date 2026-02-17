"""Feedback Agent - Intelligent conversational agent for workflow feedback.

This agent can:
1. Answer questions about workflow outputs
2. Discuss and brainstorm improvements
3. Suggest specific changes for user approval
4. Execute approved changes by invoking revision workflows
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from strands import Agent, tool

from haytham.agents.factory.agent_factory import get_bedrock_model_id
from haytham.agents.utils.model_provider import create_model

logger = logging.getLogger(__name__)

# Store for pending changes that need user approval
_pending_changes: dict[str, list[dict]] = {}


@dataclass
class FeedbackAgentContext:
    """Context for the feedback agent including workflow outputs."""

    session_dir: Path
    workflow_type: str
    workflow_stages: list[str]
    system_goal: str
    stage_outputs: dict[str, str] = field(default_factory=dict)

    def load_outputs(self) -> None:
        """Load all stage outputs into memory."""
        for stage_slug in self.workflow_stages:
            stage_dir = self.session_dir / stage_slug
            if stage_dir.exists():
                # Load all markdown files from the stage
                content_parts = []
                for md_file in sorted(stage_dir.glob("*.md")):
                    if md_file.name not in ("checkpoint.md", "user_feedback.md"):
                        try:
                            raw_content = md_file.read_text()
                            # Strip output header and check if there's real content
                            cleaned = self._strip_output_header(raw_content)
                            if cleaned:  # Only include if there's actual content
                                content_parts.append(raw_content)
                        except (OSError, UnicodeDecodeError):
                            continue
                if content_parts:
                    self.stage_outputs[stage_slug] = "\n\n---\n\n".join(content_parts)

    def _strip_output_header(self, content: str) -> str:
        """Strip output headers and check for real content."""
        # Remove "## Output" or "# Output" header
        content = re.sub(r"^#+ Output\s*\n*", "", content, flags=re.MULTILINE)
        # Remove metadata sections
        content = re.sub(
            r"^## (Metadata|Execution Details).*?(?=^## |\Z)",
            "",
            content,
            flags=re.MULTILINE | re.DOTALL,
        )
        return content.strip()


# Global context - set before agent invocation
_current_context: FeedbackAgentContext | None = None


def set_agent_context(context: FeedbackAgentContext) -> None:
    """Set the current context for the feedback agent."""
    global _current_context
    _current_context = context
    context.load_outputs()


def get_agent_context() -> FeedbackAgentContext | None:
    """Get the current context."""
    return _current_context


# =============================================================================
# Agent Tools
# =============================================================================


@tool
def read_stage_output(stage_slug: str) -> str:
    """Read the output of a specific workflow stage.

    Use this tool to look up details from a stage's output when answering
    questions or understanding what was generated.

    Args:
        stage_slug: The stage identifier (e.g., 'idea-analysis', 'risk-assessment')

    Returns:
        The stage's output content, or an error message if not found.
    """
    ctx = get_agent_context()
    if not ctx:
        return "Error: No context available."

    if stage_slug in ctx.stage_outputs:
        return ctx.stage_outputs[stage_slug]

    # Try to find partial match
    for slug in ctx.stage_outputs:
        if stage_slug in slug or slug in stage_slug:
            return ctx.stage_outputs[slug]

    available = ", ".join(ctx.stage_outputs.keys()) if ctx.stage_outputs else "none"
    return f"Stage '{stage_slug}' not found. Available stages: {available}"


@tool
def list_available_stages() -> str:
    """List all available workflow stages and their status.

    Use this to understand what stages exist and what content is available.

    Returns:
        A list of stage slugs with their availability status.
    """
    ctx = get_agent_context()
    if not ctx:
        return "Error: No context available."

    result = [f"Workflow: {ctx.workflow_type}", f"System Goal: {ctx.system_goal}", "", "Stages:"]
    for stage in ctx.workflow_stages:
        has_output = stage in ctx.stage_outputs
        status = "has output" if has_output else "no output"
        result.append(f"  - {stage}: {status}")

    return "\n".join(result)


@tool
def propose_changes(changes: list[dict]) -> str:
    """Propose specific changes to workflow stages for user approval.

    Use this when the user's request requires modifying stage outputs.
    The changes will be shown to the user for approval before execution.

    IMPORTANT: Only use this when you're confident the user wants to make changes.
    For questions or discussions, just respond directly without proposing changes.

    Args:
        changes: List of change proposals, each with:
            - stage: The stage slug to modify
            - description: What will be changed
            - instructions: Detailed instructions for the revision

    Returns:
        Confirmation that changes have been proposed for approval.

    Example:
        propose_changes([{
            "stage": "risk-assessment",
            "description": "Add analysis of competitor pricing strategies",
            "instructions": "Research and add a section analyzing how competitors price their products and how this affects our risk profile."
        }])
    """
    ctx = get_agent_context()
    if not ctx:
        return "Error: No context available."

    # Validate changes - stage must have output to be revised
    valid_changes = []
    skipped_no_output = []
    for change in changes:
        stage = change.get("stage", "")
        # Only allow changes to stages that have actual output
        if stage in ctx.stage_outputs:
            valid_changes.append(change)
        elif stage in ctx.workflow_stages:
            # Stage exists but no output yet
            skipped_no_output.append(stage)
            logger.warning(f"Skipping stage without output: {stage}")
        else:
            logger.warning(f"Skipping invalid stage: {stage}")

    if not valid_changes:
        if skipped_no_output:
            return (
                f"Cannot propose changes to stages without output: {', '.join(skipped_no_output)}. "
                "These stages haven't been completed yet."
            )
        return "No valid stages specified for changes. Please check the stage names."

    # Store pending changes
    _pending_changes[ctx.workflow_type] = valid_changes

    # Format response
    result = ["I'd like to make the following changes:", ""]
    for i, change in enumerate(valid_changes, 1):
        result.append(f"**{i}. {change.get('stage', 'Unknown')}**")
        result.append(f"   {change.get('description', 'No description')}")
        result.append("")

    result.append(
        "Would you like me to proceed with these changes? (Say 'yes' or 'go ahead' to confirm)"
    )

    return "\n".join(result)


@tool
def execute_approved_changes() -> str:
    """Execute previously proposed changes after user approval.

    Only call this after the user has approved the proposed changes.

    Returns:
        Status of the executed changes.
    """
    ctx = get_agent_context()
    if not ctx:
        return "Error: No context available."

    pending = _pending_changes.get(ctx.workflow_type, [])
    if not pending:
        return "No pending changes to execute. Please propose changes first."

    # Import here to avoid circular imports
    from haytham.feedback.revision_executor import execute_revision
    from haytham.session.session_manager import SessionManager

    session_manager = SessionManager(str(ctx.session_dir.parent))

    results = []
    for change in pending:
        stage_slug = change.get("stage", "")
        instructions = change.get("instructions", change.get("description", ""))

        try:
            result = execute_revision(
                stage_slug=stage_slug,
                feedback=instructions,
                session_manager=session_manager,
                system_goal=ctx.system_goal,
                is_cascade=False,
            )
            if result.success:
                results.append(f"- {stage_slug}: Updated successfully")
                # Reload the output
                ctx.stage_outputs[stage_slug] = result.output or ""
            else:
                results.append(f"- {stage_slug}: Failed - {result.error}")
        except Exception as e:
            results.append(f"- {stage_slug}: Error - {e}")

    # Clear pending changes
    _pending_changes[ctx.workflow_type] = []

    return "Changes applied:\n" + "\n".join(results)


@tool
def generate_missing_stage(stage_slug: str) -> str:
    """Generate output for a stage that doesn't have any content yet.

    Use this when a user asks to create or generate content for a stage that
    hasn't been completed. This runs the original agent for that stage.

    Args:
        stage_slug: The stage to generate (e.g., 'validation-summary')

    Returns:
        Status message indicating success or failure.
    """
    ctx = get_agent_context()
    if not ctx:
        return "Error: No context available."

    # Check if stage already has output
    if stage_slug in ctx.stage_outputs:
        return f"Stage '{stage_slug}' already has output. Use propose_changes to modify it instead."

    # Check if it's a valid stage
    if stage_slug not in ctx.workflow_stages:
        available = ", ".join(ctx.workflow_stages)
        return f"Unknown stage '{stage_slug}'. Available stages: {available}"

    try:
        from haytham.agents.factory.agent_factory import create_agent_by_name
        from haytham.feedback.revision_executor import _get_agents_for_stage, _save_revised_output
        from haytham.session.session_manager import SessionManager

        # Get agent(s) for this stage
        agent_names = _get_agents_for_stage(stage_slug)
        if not agent_names:
            return f"No agent configured for stage '{stage_slug}'. Cannot generate output."

        # Build context from existing stage outputs
        context_parts = [f"## System Goal\n{ctx.system_goal}"]
        for slug, content in ctx.stage_outputs.items():
            context_parts.append(f"## {slug}\n{content[:2000]}...")  # Truncate for context

        context = "\n\n".join(context_parts)

        prompt = f"""Based on the following context, generate the output for the {stage_slug} stage.

{context}

Generate comprehensive, well-structured output for this stage following your standard format.
"""

        session_manager = SessionManager(str(ctx.session_dir.parent))

        # Generate with higher max_tokens
        GENERATION_MAX_TOKENS = 4000
        outputs = []
        for agent_name in agent_names:
            logger.info(f"Generating {stage_slug} using agent '{agent_name}'")

            agent = create_agent_by_name(agent_name, max_tokens_override=GENERATION_MAX_TOKENS)
            result = agent(prompt)

            # Extract and format output using the same logic as the workflow
            from haytham.agents.output_utils import extract_text_from_result

            output = extract_text_from_result(result)
            outputs.append(output)

            # Save the output
            _save_revised_output(
                session_manager=session_manager,
                stage_slug=stage_slug,
                agent_name=agent_name,
                output=output,
            )

            # Update context
            ctx.stage_outputs[stage_slug] = output

        return f"Successfully generated output for '{stage_slug}'. The content has been saved."

    except Exception as e:
        logger.error(f"Error generating stage '{stage_slug}': {e}")
        return f"Error generating stage: {e}"


def _extract_and_format_output(result, agent_name: str) -> str:
    """Extract and format output from agent result.

    Handles both regular text output and structured output (Pydantic models).

    Args:
        result: The agent result
        agent_name: Name of the agent (used to determine formatting)

    Returns:
        Formatted markdown string
    """
    # Check for structured output first
    if hasattr(result, "parsed") and result.parsed is not None:
        # Structured output from Strands SDK
        parsed = result.parsed
        return _format_structured_output(parsed, agent_name)

    # Handle Pydantic model directly
    if hasattr(result, "model_dump"):
        return _format_structured_output(result, agent_name)

    # Handle dict formats
    if isinstance(result, dict):
        # Check for toolUse wrapper (Strands SDK structured output format)
        if "toolUse" in result:
            tool_use = result["toolUse"]
            if isinstance(tool_use, dict) and "input" in tool_use:
                return _format_structured_output(tool_use["input"], agent_name)

        # Check for content array with toolUse
        if "content" in result:
            content = result["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "toolUse" in item:
                        tool_use = item["toolUse"]
                        if isinstance(tool_use, dict) and "input" in tool_use:
                            return _format_structured_output(tool_use["input"], agent_name)

        # Direct structured output dict
        if "recommendation" in result and "executive_summary" in result:
            return _format_structured_output(result, agent_name)

    # Check message content for toolUse
    if hasattr(result, "message") and result.message:
        message = result.message
        if isinstance(message, dict) and "content" in message:
            content = message["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "toolUse" in item:
                        tool_use = item["toolUse"]
                        if isinstance(tool_use, dict) and "input" in tool_use:
                            return _format_structured_output(tool_use["input"], agent_name)

    # Fall back to text extraction
    return _extract_text_output(result)


def _format_structured_output(data, agent_name: str) -> str:
    """Format structured output based on agent type."""
    # Handle validation_summary specifically
    if agent_name in ("validation_scorer", "validation_narrator"):
        try:
            from haytham.agents.worker_validation_summary.validation_summary_models import (
                format_validation_summary,
            )

            return format_validation_summary(data)
        except Exception as e:
            logger.warning(f"Failed to format validation summary: {e}")

    # Generic fallback: convert to readable format
    if hasattr(data, "model_dump"):
        data = data.model_dump()

    if isinstance(data, dict):
        return f"```json\n{json.dumps(data, indent=2)}\n```"

    return str(data)


def _extract_text_output(result) -> str:
    """Extract text from agent result."""
    from haytham.agents.output_utils import extract_text_from_result

    return extract_text_from_result(result)


def get_pending_changes(workflow_type: str) -> list[dict]:
    """Get any pending changes for a workflow."""
    return _pending_changes.get(workflow_type, [])


def clear_pending_changes(workflow_type: str) -> None:
    """Clear pending changes for a workflow."""
    _pending_changes[workflow_type] = []


# =============================================================================
# Agent Creation
# =============================================================================

FEEDBACK_AGENT_PROMPT = """You are a helpful assistant that helps users understand and refine their startup validation results.

## CRITICAL RULES

1. **NEVER claim to have made changes unless you called propose_changes and then execute_approved_changes**
2. **NEVER say "I've updated" or "I've changed" anything without actually using the tools**
3. **For questions and explanations: Use read_stage_output to look up info, then answer directly**
4. **Only propose changes when the user EXPLICITLY asks to modify, add, remove, or change something**

## Finding Content Across Stages

You receive a preview of all stage outputs in every message context. When a user references specific text:
1. Search through ALL stage previews to find where the text appears — do NOT assume which stage it's in
2. Users may use informal names for stages (e.g., "idea expansion" could mean any stage)
3. If you can't find text in the preview, use read_stage_output to check the full content of EVERY stage
4. NEVER tell the user their text doesn't exist without checking ALL stages first

## How to Handle Different Requests

### Questions (just answer, NO changes)
User asks: "Can you explain X?" or "What is Y?" or "Why is the risk high?"
→ Use read_stage_output to get the relevant content
→ Answer the question based on what you read
→ DO NOT propose or make any changes

### Discussion (just discuss, NO changes)
User asks: "Help me think about..." or "What do you think of..." or "How could I improve..."
→ Use read_stage_output to understand the current content
→ Discuss ideas and give suggestions conversationally
→ DO NOT propose changes unless user explicitly asks

### Change Requests (propose changes, wait for approval)
User explicitly says: "Change X to Y" or "Add Z to the analysis" or "Remove W"
→ Use propose_changes tool to describe what will change
→ Wait for user to say "yes", "go ahead", "proceed", etc.
→ Only then use execute_approved_changes

### Approval (execute previously proposed changes)
User says: "yes", "go ahead", "do it", "proceed"
→ Use execute_approved_changes to apply pending changes

### Generate Missing Stage
User asks: "Generate the validation summary" or "Create the missing stage"
→ First use list_available_stages to check if the stage has output
→ If stage shows "no output", use generate_missing_stage to create content
→ Do NOT use propose_changes for stages without output - it will fail
→ After generation succeeds, inform the user the content was created

## Available Tools

- **read_stage_output**: Read content from a workflow stage (USE THIS for questions)
- **list_available_stages**: See what stages exist and have content
- **propose_changes**: Propose modifications (USE THIS only for explicit change requests)
- **execute_approved_changes**: Apply changes after user approval
- **generate_missing_stage**: Generate content for stages that don't have output yet

## Examples

User: "Can you explain the competitor landscape in one paragraph?"
→ Use read_stage_output("market-context")
→ Read the content and summarize the competitor landscape
→ DO NOT say you updated anything

User: "Add a competitor called Acme Corp to the analysis"
→ Use propose_changes with the specific change
→ Wait for approval before executing

User: "What's the risk level and why?"
→ Use read_stage_output("risk-assessment")
→ Explain the risk level based on the content
→ DO NOT make any changes
"""


def create_feedback_agent(model_id: str | None = None) -> Agent:
    """Create the feedback agent with conversation and revision capabilities.

    Args:
        model_id: Optional Bedrock model ID override

    Returns:
        Configured feedback Agent instance
    """
    if model_id is None:
        model_id = get_bedrock_model_id()

    model = create_model(
        model_id=model_id,
        max_tokens=4000,
    )

    agent = Agent(
        system_prompt=FEEDBACK_AGENT_PROMPT,
        name="feedback_agent",
        model=model,
        tools=[
            read_stage_output,
            list_available_stages,
            propose_changes,
            execute_approved_changes,
            generate_missing_stage,
        ],
    )

    logger.info("Created feedback_agent with conversation and revision tools")

    return agent


# =============================================================================
# Conversation Interface
# =============================================================================


@dataclass
class ConversationMessage:
    """A message in the feedback conversation."""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class FeedbackConversation:
    """Manages a feedback conversation with the agent."""

    context: FeedbackAgentContext
    messages: list[ConversationMessage] = field(default_factory=list)
    _agent: Agent | None = None

    def _get_agent(self) -> Agent:
        """Get or create the agent."""
        if self._agent is None:
            self._agent = create_feedback_agent()
        return self._agent

    def send_message(self, user_message: str) -> str:
        """Send a message and get a response.

        Args:
            user_message: The user's message

        Returns:
            The agent's response
        """
        # Set context for tools
        set_agent_context(self.context)

        # Add user message to history
        self.messages.append(ConversationMessage(role="user", content=user_message))

        # Build conversation history for the agent
        history = []
        for msg in self.messages[:-1]:  # Exclude the current message
            history.append({"role": msg.role, "content": msg.content})

        # Get agent
        agent = self._get_agent()

        # Build the prompt with context summary including stage content previews
        # so the agent can identify which stage contains text the user references
        context_parts = [
            f"Current workflow: {self.context.workflow_type}",
            f"System goal: {self.context.system_goal}",
            f"Available stages: {', '.join(self.context.workflow_stages)}",
            "",
            "## Current Stage Outputs",
            "Below is the content of each completed stage. Use this to find "
            "text the user references and answer questions directly.",
        ]

        MAX_CHARS_PER_STAGE = 3000
        for stage_slug in self.context.workflow_stages:
            if stage_slug in self.context.stage_outputs:
                content = self.context.stage_outputs[stage_slug]
                if len(content) > MAX_CHARS_PER_STAGE:
                    content = (
                        content[:MAX_CHARS_PER_STAGE]
                        + "\n... (truncated, use read_stage_output tool for full content)"
                    )
                context_parts.append(f"\n### {stage_slug}\n{content}")

        context_summary = "\n".join(context_parts)

        full_message = f"{context_summary}\n\nUser message: {user_message}"

        try:
            # Call the agent
            result = agent(full_message, history=history if history else None)

            # Extract response text - handle various Strands SDK response formats
            response = self._extract_response_text(result)

            # Add assistant response to history
            self.messages.append(ConversationMessage(role="assistant", content=response))

            return response

        except Exception as e:
            logger.error(f"Error in feedback agent: {e}")
            error_response = (
                f"I encountered an error processing your request: {e}. Could you try rephrasing?"
            )
            self.messages.append(ConversationMessage(role="assistant", content=error_response))
            return error_response

    def _extract_response_text(self, result) -> str:
        """Extract text from Strands SDK agent result."""
        from haytham.agents.output_utils import extract_text_from_result

        try:
            return extract_text_from_result(result)
        except Exception as e:
            logger.warning(f"Failed to extract response text: {e}")
            return str(result)

    def has_pending_changes(self) -> bool:
        """Check if there are pending changes awaiting approval."""
        return bool(get_pending_changes(self.context.workflow_type))

    def get_pending_changes(self) -> list[dict]:
        """Get the pending changes."""
        return get_pending_changes(self.context.workflow_type)

    def clear_pending_changes(self) -> None:
        """Clear pending changes."""
        clear_pending_changes(self.context.workflow_type)
