"""Shared agent output extraction and formatting utilities.

Canonical implementations for extracting text and JSON from agent results,
and formatting Pydantic models, dicts, and tool-use blocks as markdown.
All callers should import from this module instead of re-implementing.

Extraction functions:
- extract_output_content(full_content) -> str: Extract ## Output section from saved markdown
- extract_text_from_result(result) -> str: Extract text from any agent result format
- extract_json_from_text(text) -> dict | None: Extract JSON from markdown/text

Formatting functions (used by extraction and by workflow layer):
- _format_pydantic_model_as_markdown(model) -> str
- _format_tool_use_output(tool_use) -> str
- _format_validation_summary_output(data) -> str
- _format_validation_output(data) -> str
- _format_dict_as_markdown(data) -> str
"""

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Compiled regex patterns (module-level for performance)
_THINKING_TAG_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)
_JSON_CODE_BLOCK_RE = re.compile(r"```json\s*([\s\S]*?)```")
_ANY_CODE_BLOCK_RE = re.compile(r"```\s*([\s\S]*?)```")
_SWARM_RESULT_TEXT_RE = re.compile(r"'text':\s*'([^']*(?:''[^']*)*)'")

# Known metadata section headers that should be stripped from output content
_KNOWN_METADATA_SECTIONS = [
    "## Error Details",
    "## Metadata",
    "## Execution Details",
    "## Debug Info",
    "## Stack Trace",
]


def extract_output_content(full_content: str) -> str:
    """Extract the ``## Output`` section from a saved agent output markdown file.

    Handles:
    - Raw ``SwarmResult(...)`` strings from old buggy saves (extracts 'text' fields)
    - Known metadata sections (``## Error Details``, ``## Metadata``, etc.) are stripped

    Args:
        full_content: Full agent output file content (markdown)

    Returns:
        Extracted output content (stripped of metadata)
    """
    if "## Output" not in full_content:
        return full_content

    parts = full_content.split("## Output", 1)
    if len(parts) < 2:
        return full_content

    output_section = parts[1]

    # Handle raw SwarmResult string from old buggy saves
    if "SwarmResult(" in output_section and "'text':" in output_section:
        text_matches = _SWARM_RESULT_TEXT_RE.findall(output_section)
        if text_matches:
            extracted_text = "\n\n".join(text_matches)
            extracted_text = extracted_text.replace("\\n", "\n")
            extracted_text = extracted_text.replace("\\t", "\t")
            extracted_text = extracted_text.replace("\\'", "'")
            return extracted_text.strip()

    # Strip known metadata sections
    result_lines = []
    for line in output_section.split("\n"):
        if any(line.strip().startswith(section) for section in _KNOWN_METADATA_SECTIONS):
            break
        result_lines.append(line)

    return "\n".join(result_lines).strip()


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
    # --- StageOutput envelope (ADR-022) ---
    # Lazy import: agents/ → workflow/ cross-boundary (would create circular dep
    # since workflow/ imports from agents/output_utils at module level).
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

    return _format_pydantic_model_as_markdown(model)


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
    return _format_dict_as_markdown(result)


def _format_tool_use(tool_use: Any) -> str:
    """Format a toolUse block as readable text."""
    if isinstance(tool_use, dict):
        return _format_tool_use_output(tool_use)
    return str(tool_use)


def _format_pydantic_model_as_markdown(model: Any) -> str:
    """Format a Pydantic model as human-readable markdown.

    Prefers the model's own ``to_markdown()`` method (all output models
    should implement it). Falls back to a generic ``model_dump()`` renderer.

    Args:
        model: A Pydantic BaseModel instance

    Returns:
        Formatted markdown string
    """
    if not isinstance(model, BaseModel):
        return ""

    # Primary: use the model's own to_markdown()
    if hasattr(model, "to_markdown") and callable(model.to_markdown):
        try:
            result = model.to_markdown()
            if result and result.strip():
                return result
        except (TypeError, AttributeError, ValueError):
            pass  # Fall through to generic rendering

    # Generic fallback: render model_dump() as markdown
    try:
        data = model.model_dump()
        lines: list[str] = ["# Structured Output\n"]
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"## {key.replace('_', ' ').title()}\n")
                for i, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        lines.append(f"### Item {i}")
                        for k, v in item.items():
                            lines.append(f"- **{k}:** {v}")
                        lines.append("")
                    else:
                        lines.append(f"- {item}")
            elif isinstance(value, dict):
                lines.append(f"## {key.replace('_', ' ').title()}\n")
                for k, v in value.items():
                    lines.append(f"- **{k}:** {v}")
                lines.append("")
            else:
                lines.append(f"**{key.replace('_', ' ').title()}:** {value}\n")
    except (TypeError, AttributeError, ValueError):
        return str(model)

    return "\n".join(lines)


def _format_tool_use_output(tool_use: dict) -> str:
    """Format tool use output as readable markdown."""
    if not isinstance(tool_use, dict):
        return str(tool_use)

    tool_name = tool_use.get("name", "Unknown Tool")
    tool_input = tool_use.get("input", {})

    formatter = _TOOL_OUTPUT_FORMATTERS.get(tool_name)
    if formatter is not None and isinstance(tool_input, dict):
        return formatter(tool_input)

    return _format_dict_as_markdown(tool_input)


def _format_validation_summary_output(data: dict) -> str:
    """Format ValidationSummaryOutput tool response as markdown."""
    lines = ["# Validation Summary\n"]

    # Executive Summary
    if "executive_summary" in data:
        lines.append("## Executive Summary\n")
        lines.append(data["executive_summary"])
        lines.append("")

    # Validation Findings
    if "validation_findings" in data:
        findings = data["validation_findings"]
        lines.append("---\n")
        lines.append("## Validation Findings\n")

        if "market_opportunity" in findings:
            lines.append("### Market Opportunity\n")
            lines.append(findings["market_opportunity"])
            lines.append("")

        if "competition" in findings:
            lines.append("### Competition\n")
            lines.append(findings["competition"])
            lines.append("")

        if "critical_risks" in findings:
            lines.append("### Critical Risks\n")
            for risk in findings["critical_risks"]:
                lines.append(f"- {risk}")
            lines.append("")

    # Go/No-Go Assessment
    if "go_no_go_assessment" in data:
        assessment = data["go_no_go_assessment"]
        lines.append("---\n")
        lines.append("## Go/No-Go Assessment\n")

        if "strengths" in assessment:
            lines.append("### Strengths\n")
            for s in assessment["strengths"]:
                lines.append(f"- {s}")
            lines.append("")

        if "weaknesses" in assessment:
            lines.append("### Weaknesses\n")
            for w in assessment["weaknesses"]:
                lines.append(f"- {w}")
            lines.append("")

        if "counter_signals" in assessment and assessment["counter_signals"]:
            lines.append("### Counter-Signals Reconciliation\n")
            for cs in assessment["counter_signals"]:
                dims = ", ".join(cs.get("affected_dimensions", []))
                lines.append(
                    f"- **{cs.get('signal', '')}** (source: {cs.get('source', '?')}, affects: {dims})"
                )
                # Prefer structured fields; fall back to legacy reconciliation
                if (
                    cs.get("evidence_cited")
                    or cs.get("why_score_holds")
                    or cs.get("what_would_change_score")
                ):
                    if cs.get("evidence_cited"):
                        lines.append(f"  - *Evidence cited:* {cs['evidence_cited']}")
                    if cs.get("why_score_holds"):
                        lines.append(f"  - *Why score holds:* {cs['why_score_holds']}")
                    if cs.get("what_would_change_score"):
                        lines.append(
                            f"  - *What would change score:* {cs['what_would_change_score']}"
                        )
                elif cs.get("reconciliation"):
                    lines.append(f"  - *Reconciliation:* {cs['reconciliation']}")
            lines.append("")

        if "guidance" in assessment:
            lines.append("### Guidance\n")
            lines.append(assessment["guidance"])
            lines.append("")

    # Next Steps
    if "next_steps" in data:
        lines.append("---\n")
        lines.append("## Next Steps\n")
        for i, step in enumerate(data["next_steps"], 1):
            lines.append(f"{i}. {step}")

    return "\n".join(lines)


def _format_validation_output(data: dict) -> str:
    """Format ValidationOutput tool response as markdown."""
    lines = ["# Risk Assessment Report\n"]

    # Summary section
    summary = data.get("summary", {})
    if summary:
        lines.append("## Summary\n")
        lines.append(f"- **Total Claims Analyzed:** {summary.get('total_claims', 'N/A')}")
        lines.append(f"- **Supported:** {summary.get('supported', 0)}")
        lines.append(f"- **Partial:** {summary.get('partial', 0)}")
        lines.append(f"- **Unsupported:** {summary.get('unsupported', 0)}")
        lines.append(f"- **High Risks:** {summary.get('high_risks', 0)}")
        lines.append(f"- **Medium Risks:** {summary.get('medium_risks', 0)}")
        lines.append("")

    # Risks section
    risks = data.get("risks", [])
    if risks:
        lines.append("## Identified Risks\n")
        for risk in risks:
            level = risk.get("level", "unknown").upper()
            desc = risk.get("description", "No description")
            mitigation = risk.get("mitigation", "No mitigation suggested")
            lines.append(f"### Risk ({level})")
            lines.append(f"**Description:** {desc}\n")
            lines.append(f"**Mitigation:** {mitigation}\n")

    # Claims section
    claims = data.get("claims", [])
    if claims:
        lines.append("## Claims Analysis\n")
        for claim in claims[:5]:  # Limit to first 5 claims
            text = claim.get("text", "")
            validation = claim.get("validation", "unknown")
            reasoning = claim.get("reasoning", "")
            lines.append(f"- **{validation.upper()}:** {text}")
            if reasoning:
                lines.append(f"  - *{reasoning}*")
        if len(claims) > 5:
            lines.append(f"\n*...and {len(claims) - 5} more claims*")

    return "\n".join(lines)


_TOOL_OUTPUT_FORMATTERS: dict[str, Callable[[dict], str]] = {
    "ValidationOutput": _format_validation_output,
    "ValidationSummaryOutput": _format_validation_summary_output,
}


def _format_dict_as_markdown(data: dict) -> str:
    """Format a dictionary as readable markdown."""
    if not isinstance(data, dict):
        return str(data)

    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"## {key.replace('_', ' ').title()}\n")
            for k, v in value.items():
                lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
        elif isinstance(value, list):
            lines.append(f"## {key.replace('_', ' ').title()}\n")
            for item in value[:10]:  # Limit list items
                if isinstance(item, dict):
                    # Format dict item
                    item_str = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:3])
                    lines.append(f"- {item_str}")
                else:
                    lines.append(f"- {item}")
        else:
            lines.append(f"**{key.replace('_', ' ').title()}:** {value}")

    return "\n".join(lines) if lines else str(data)


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

        if ch == '"':
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
