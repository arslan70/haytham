"""Shared agent output extraction utilities.

Canonical implementations for extracting text and JSON from agent results.
All callers should import from this module instead of re-implementing.

Two main functions:
- extract_text_from_result(result) -> str: Extract text from any agent result format
- extract_json_from_text(text) -> dict | None: Extract JSON from markdown/text
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Compiled regex patterns (module-level for performance)
_THINKING_TAG_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)
_JSON_CODE_BLOCK_RE = re.compile(r"```json\s*([\s\S]*?)```")
_ANY_CODE_BLOCK_RE = re.compile(r"```\s*([\s\S]*?)```")


def extract_text_from_result(result: Any, output_as_json: bool = False) -> str:
    """Extract text output from various agent result formats.

    Handles: StageOutput, Pydantic BaseModel, AgentResult (dict message,
    object message), plain string, dict, and toolUse formatting.

    Strips ``<thinking>`` tags from the output.

    Args:
        result: Raw agent result (AgentResult, Pydantic model, dict, str, etc.)
        output_as_json: If True and result has a Pydantic structured output,
            return model_dump_json() instead of rendering markdown.
    """
    from pydantic import BaseModel

    # --- StageOutput envelope (ADR-022) ---
    try:
        from haytham.workflow.stage_output import StageOutput

        if isinstance(result, StageOutput):
            return result.to_markdown().strip()

        if hasattr(result, "structured_output") and isinstance(
            result.structured_output, StageOutput
        ):
            return result.structured_output.to_markdown().strip()
    except ImportError:
        pass

    output_text = ""

    # --- JSON mode: return model_dump_json for Pydantic structured outputs ---
    if output_as_json:
        if isinstance(result, BaseModel):
            return result.model_dump_json()
        if hasattr(result, "structured_output") and result.structured_output is not None:
            if isinstance(result.structured_output, BaseModel):
                return result.structured_output.model_dump_json()

    # --- Pydantic model → markdown ---
    if isinstance(result, BaseModel):
        output_text = _format_model_as_markdown(result)
        if output_text:
            return output_text.strip()

    # --- AgentResult structured_output (Strands SDK) ---
    if hasattr(result, "structured_output") and result.structured_output is not None:
        if isinstance(result.structured_output, BaseModel):
            output_text = _format_model_as_markdown(result.structured_output)
            if output_text:
                return output_text.strip()

    # --- AgentResult with message attribute ---
    if hasattr(result, "message"):
        output_text = _extract_from_message(result.message)

    # --- Direct string ---
    elif isinstance(result, str):
        output_text = result

    # --- Dict result ---
    elif isinstance(result, dict):
        output_text = _extract_from_dict(result)

    else:
        output_text = str(result)

    # Strip thinking tags
    output_text = _THINKING_TAG_RE.sub("", output_text)

    return output_text.strip()


def extract_json_from_text(text: str) -> dict | None:
    """Extract and parse JSON from text that may contain markdown code blocks.

    Strategy chain (most specific → most permissive):
    1. Direct ``json.loads()`` (for pure JSON input)
    2. Regex code block: ````` ```json ... ``` ````` or ````` ``` ... ``` `````
    3. Character scan for ``{`` to matching ``}`` (handles orphaned JSON)

    Returns:
        Parsed dict, or None if no valid JSON found.
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # 1. Direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Regex: ```json ... ``` block
    match = _JSON_CODE_BLOCK_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 2b. Regex: ``` ... ``` block (no json tag)
    match = _ANY_CODE_BLOCK_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 3. Character scan: find first { and its matching }
    return _scan_json_object(text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_model_as_markdown(model: Any) -> str:
    """Format a Pydantic model as markdown, preferring to_markdown()."""
    if hasattr(model, "to_markdown") and callable(model.to_markdown):
        try:
            result = model.to_markdown()
            if result and result.strip():
                return result
        except (AttributeError, TypeError, ValueError) as e:
            logger.debug("to_markdown() failed for %s: %s", type(model).__name__, e)

    # Delegate to burr_actions' full formatter for backward compat.
    # This import is deferred to avoid circular imports.
    try:
        from haytham.workflow.burr_actions import _format_pydantic_model_as_markdown

        return _format_pydantic_model_as_markdown(model)
    except ImportError:
        pass

    return str(model)


def _extract_from_message(msg: Any) -> str:
    """Extract text from a Strands message (dict or object)."""
    # Dict with content array
    if isinstance(msg, dict) and "content" in msg:
        return _extract_from_content(msg["content"])

    # Object with content attribute
    if hasattr(msg, "content"):
        return _extract_from_content(msg.content)

    return str(msg)


def _extract_from_content(content: Any) -> str:
    """Extract text from a content value (list of blocks or string)."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    parts.append(item["text"])
                elif "toolUse" in item:
                    parts.append(_format_tool_use(item["toolUse"]))
            elif hasattr(item, "text"):
                parts.append(item.text)
            elif hasattr(item, "toolUse"):
                parts.append(_format_tool_use(item.toolUse))
        if parts:
            return "".join(parts)
        # No text or toolUse content found — return empty to trigger
        # the empty-output check upstream rather than saving str([...])
        logger.warning("No text content extracted from content list (%d items)", len(content))
        return ""

    return str(content)


def _extract_from_dict(result: dict) -> str:
    """Extract text from a dict-shaped result."""
    if "content" in result:
        return _extract_from_content(result["content"])
    if "output" in result:
        return str(result["output"])
    if "text" in result:
        return result["text"]
    # Fallback: format dict as markdown
    try:
        from haytham.workflow.burr_actions import _format_dict_as_markdown

        return _format_dict_as_markdown(result)
    except ImportError:
        return str(result)


def _format_tool_use(tool_use: Any) -> str:
    """Format a toolUse block as readable text."""
    try:
        from haytham.workflow.burr_actions import _format_tool_use_output

        return _format_tool_use_output(tool_use)
    except ImportError:
        pass

    if isinstance(tool_use, dict):
        tool_input = tool_use.get("input", {})
        if isinstance(tool_input, dict):
            return json.dumps(tool_input, indent=2)
        return str(tool_input)
    return str(tool_use)


def _scan_json_object(text: str) -> dict | None:
    """Scan text for the first balanced JSON object { ... }."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if ch == '"' and not escape:
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    return None

    return None
