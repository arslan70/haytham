"""Output Formatter Service for Haytham.

This module centralizes all output formatting, content extraction, and
parsing logic that was previously scattered throughout app.py.

Design Principles:
- Single Responsibility: Only handles output formatting and extraction
- Open/Closed: New extractors can be added via STAGE_EXTRACTORS dict
- Strategy Pattern: Extractors are data-driven configurations
- DRY: Eliminates duplicated extraction patterns

Usage:
    from haytham.formatters import OutputFormatter

    formatter = OutputFormatter()
    highlights = formatter.extract_highlights("idea-analysis", content)
    clean_content = formatter.clean_output(content)
"""

import json
import logging
import re
from collections.abc import Callable

from haytham.config import (
    AGENT_PREAMBLE_PATTERNS,
    DEFAULT_EXTRACT_ITEMS,
    DEFAULT_ITEM_CHARS,
    DEFAULT_SECTION_CHARS,
    DEFAULT_SECTION_LINES,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Text Cleaning Utilities
# =============================================================================


def strip_thinking_tags(content: str) -> str:
    """Remove <thinking>...</thinking> tags and their content from output."""
    content = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL | re.IGNORECASE)
    return content.strip()


def skip_agent_preamble(content: str) -> str:
    """Skip agent preamble/thinking text and get to actual content."""
    lines = content.split("\n")
    start_idx = 0

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Skip empty lines at start
        if not line_lower:
            continue

        # Found a non-preamble line - check if it's real content
        if not any(pattern in line_lower for pattern in AGENT_PREAMBLE_PATTERNS):
            start_idx = i
            break

    return "\n".join(lines[start_idx:])


# =============================================================================
# JSON Parsing
# =============================================================================


def try_parse_json(content: str) -> dict | None:
    """Try to parse JSON from content string.

    Handles various formats:
    - Pure JSON string
    - JSON with text before/after
    - JSON inside markdown code blocks

    Args:
        content: String that may contain JSON

    Returns:
        Parsed dict if successful, None otherwise
    """
    if not content or not content.strip():
        return None

    # Try 1: Direct parse (pure JSON)
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try 2: Extract from markdown code blocks (```json ... ```)
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try 3: Find first complete JSON object using brace matching
    json_start = content.find("{")
    if json_start >= 0:
        brace_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(content[json_start:], start=json_start):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    # Found complete JSON object
                    json_str = content[json_start : i + 1]
                    try:
                        return json.loads(json_str)
                    except (json.JSONDecodeError, ValueError):
                        break  # Malformed, try next approach

    # Try 4: Simple first { to last } (may fail with multiple objects)
    json_start = content.find("{")
    json_end = content.rfind("}") + 1
    if json_start >= 0 and json_end > json_start:
        try:
            return json.loads(content[json_start:json_end])
        except (json.JSONDecodeError, ValueError):
            pass

    return None


# =============================================================================
# Content Extractors
# =============================================================================


def _extract_section_content(
    content: str,
    keyword: str,
    max_lines: int = DEFAULT_SECTION_LINES,
    max_chars: int = DEFAULT_SECTION_CHARS,
) -> str | None:
    """Extract content following a section header with keyword.

    Common pattern used across multiple extractors.

    Args:
        content: Full content string
        keyword: Keyword to search for in headers
        max_lines: Maximum lines to extract
        max_chars: Maximum characters to return

    Returns:
        Extracted content or None
    """
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if keyword in line.lower() and (":" in line or "#" in line):
            desc_lines = []
            for j in range(i + 1, min(i + max_lines, len(lines))):
                if lines[j].strip() and not lines[j].startswith("#"):
                    desc_lines.append(lines[j].strip())
                elif lines[j].startswith("#"):
                    break
            if desc_lines:
                return " ".join(desc_lines)[:max_chars]
    return None


def _extract_list_items(
    content: str,
    keyword: str,
    max_items: int = DEFAULT_EXTRACT_ITEMS,
    max_item_chars: int = DEFAULT_ITEM_CHARS,
) -> list[str]:
    """Extract list items following a section header.

    Args:
        content: Full content string
        keyword: Keyword to search for in headers
        max_items: Maximum items to extract
        max_item_chars: Maximum characters per item

    Returns:
        List of extracted items
    """
    lines = content.split("\n")
    items = []
    for i, line in enumerate(lines):
        if keyword in line.lower() and "#" in line:
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip().startswith("-"):
                    item = lines[j].strip().lstrip("-").strip()
                    if item and len(item) > 5:
                        # Clean up the item text
                        item = item.split("(")[0].strip()  # Remove parenthetical
                        items.append(item[:max_item_chars])
                        if len(items) >= max_items:
                            return items
                elif lines[j].startswith("#"):
                    break
    return items


def extract_concept_highlights(content: str) -> str:
    """Extract key highlights from concept expansion output."""
    content = skip_agent_preamble(content)
    highlights = []

    # Look for problem statement
    problem = _extract_section_content(content, "problem")
    if problem:
        highlights.append(f"**Problem:** {problem}...")

    # Look for solution
    solution = _extract_section_content(content, "solution")
    if solution:
        highlights.append(f"**Solution:** {solution}...")

    # Look for target audience/users
    for keyword in ["target", "audience", "user", "customer"]:
        target = _extract_section_content(content, keyword, max_lines=3, max_chars=100)
        if target:
            highlights.append(f"**Target:** {target}...")
            break

    if highlights:
        return "\n".join(highlights) + "\n\n"

    # Fallback: first meaningful paragraph
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")]
    if paragraphs:
        return f"*{paragraphs[0][:200]}...*\n\n"
    return "*Phase completed*\n\n"


def extract_market_highlights(market_content: str, competitor_content: str = "") -> str:
    """Extract key highlights from market research outputs."""
    clean_market = skip_agent_preamble(market_content)
    highlights = []

    # Look for customer segments
    segments = _extract_list_items(clean_market, "segment", max_items=2, max_item_chars=40)
    if not segments:
        segments = _extract_list_items(clean_market, "customer", max_items=2, max_item_chars=40)
    if segments:
        highlights.append(f"**Segments:** {', '.join(segments)}")

    # Look for opportunities
    if "opportunit" in clean_market.lower():
        lines = clean_market.split("\n")
        for i, line in enumerate(lines):
            if "opportunit" in line.lower() and (":" in line or "#" in line):
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip().startswith("-"):
                        opp = lines[j].strip().lstrip("-").strip()
                        if opp and len(opp) > 15:
                            highlights.append(f"**Opportunity:** {opp[:80]}...")
                            break
                    elif lines[j].startswith("#"):
                        break
                break

    # Look for market trends
    trends = _extract_list_items(clean_market, "trend", max_items=2, max_item_chars=50)
    if trends:
        highlights.append(f"**Trends:** {', '.join(trends)}")

    # Look for market size (TAM, SAM, SOM)
    for keyword in ["tam", "market size", "total addressable", "billion", "million"]:
        if keyword in clean_market.lower():
            lines = clean_market.split("\n")
            for line in lines:
                if keyword in line.lower() and any(c.isdigit() for c in line):
                    clean_line = line.strip().lstrip("-*#").strip()
                    if clean_line and len(clean_line) > 5 and "$" in clean_line:
                        highlights.append(f"**Market Size:** {clean_line[:60]}")
                        break
            break

    if highlights:
        return "\n".join(highlights) + "\n\n"

    # Fallback
    lines = clean_market.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#") and not line.startswith("##"):
            for j in range(i + 1, min(i + 8, len(lines))):
                para = lines[j].strip()
                if para and not para.startswith("#") and len(para) > 30:
                    if para.startswith("-"):
                        para = para.lstrip("-").strip()
                    return f"*{para[:120]}...*\n\n"

    return "*Market research completed*\n\n"


def extract_niche_highlights(niche_content: str, decision_content: str = "") -> str:
    """Extract key highlights from niche selection outputs."""
    niche_content = skip_agent_preamble(niche_content)
    highlights = []

    # Look for selected niche or recommendation
    for keyword in ["recommend", "selected", "niche", "segment", "focus"]:
        if keyword in niche_content.lower():
            lines = niche_content.split("\n")
            for i, line in enumerate(lines):
                if keyword in line.lower():
                    if ":" in line:
                        value = line.split(":", 1)[1].strip()
                        if value:
                            highlights.append(f"**Focus:** {value[:100]}")
                            break
                    elif i + 1 < len(lines) and lines[i + 1].strip():
                        highlights.append(f"**Focus:** {lines[i + 1].strip()[:100]}")
                        break
            break

    # Look for opportunity
    opp = _extract_section_content(niche_content, "opportunity", max_lines=2, max_chars=100)
    if opp:
        highlights.append(f"**Opportunity:** {opp}")

    if highlights:
        return "\n".join(highlights) + "\n\n"

    preview = niche_content[:150].replace("\n", " ").strip()
    return f"*{preview}...*\n\n" if preview else "*Phase completed*\n\n"


def extract_strategy_highlights(content: str) -> str:
    """Extract key highlights from product strategy output."""
    content = skip_agent_preamble(content)
    highlights = []

    # Look for MVP features
    for keyword in ["mvp", "feature", "core"]:
        features = _extract_list_items(content, keyword, max_items=3, max_item_chars=50)
        if features:
            highlights.append(f"**MVP Features:** {', '.join(features)}")
            break

    if highlights:
        return "\n".join(highlights) + "\n\n"

    preview = content[:150].replace("\n", " ").strip()
    return f"*{preview}...*\n\n" if preview else "*Phase completed*\n\n"


def extract_business_highlights(content: str) -> str:
    """Extract key highlights from business planning output."""
    content = skip_agent_preamble(content)
    highlights = []

    # Look for revenue model
    for keyword in ["revenue", "pricing", "monetization"]:
        if keyword in content.lower():
            lines = content.split("\n")
            for line in lines:
                if keyword in line.lower():
                    clean = line.strip().lstrip("-*#").strip()
                    if clean and len(clean) > 10:
                        highlights.append(f"**Revenue:** {clean[:100]}")
                        break
            break

    if highlights:
        return "\n".join(highlights) + "\n\n"

    preview = content[:150].replace("\n", " ").strip()
    return f"*{preview}...*\n\n" if preview else "*Phase completed*\n\n"


def extract_validation_highlights(content: str) -> str:
    """Extract key highlights from validation output."""
    content = strip_thinking_tags(content)
    content = skip_agent_preamble(content)

    # Try to parse as JSON
    data = try_parse_json(content)
    if data is not None:
        highlights = []
        summary = data.get("summary", {})
        claims = data.get("claims", [])

        # Handle claims_extraction format (Phase 6A)
        if summary.get("market_claims") is not None:
            total = summary.get("total_claims", len(claims))
            market = summary.get("market_claims", 0)
            product = summary.get("product_claims", 0)
            financial = summary.get("financial_claims", 0)

            highlights.append(f"**Claims Extracted:** {total}")
            highlights.append(f"- Market: {market}, Product: {product}, Financial: {financial}")

        # Handle validation output with claims
        elif claims and any(c.get("validation") for c in claims):
            supported = partial = unsupported = 0
            for claim in claims:
                validation = claim.get("validation", "")
                if isinstance(validation, str):
                    label = validation.lower()
                    if label == "supported":
                        supported += 1
                    elif label == "partial":
                        partial += 1
                    else:
                        unsupported += 1
                elif isinstance(validation, dict):
                    track1 = validation.get("track_1_evidence_quality", {})
                    label = track1.get("validation_label", "").lower()
                    if "supported" in label and "partial" not in label:
                        supported += 1
                    elif "partial" in label:
                        partial += 1
                    else:
                        unsupported += 1

            total = len(claims)
            highlights.append(f"**Claims Validated:** {total}")
            highlights.append(
                f"- Supported: {supported}, Partial: {partial}, Unsupported: {unsupported}"
            )

        if highlights:
            return "\n".join(highlights) + "\n\n"

    # Fallback for non-JSON content
    preview = content[:200].replace("\n", " ").strip()
    return f"*{preview}...*\n\n" if preview else "*Validation completed*\n\n"


def extract_risk_highlights(content: str) -> str:
    """Extract key highlights from risk assessment output."""
    content = strip_thinking_tags(content)
    content = skip_agent_preamble(content)
    highlights = []

    # Look for risk level
    content_upper = content.upper()
    if "RISK LEVEL: HIGH" in content_upper or "OVERALL RISK: HIGH" in content_upper:
        highlights.append("**Risk Level:** HIGH")
    elif "RISK LEVEL: LOW" in content_upper or "OVERALL RISK: LOW" in content_upper:
        highlights.append("**Risk Level:** LOW")
    elif "RISK LEVEL: MEDIUM" in content_upper or "OVERALL RISK: MEDIUM" in content_upper:
        highlights.append("**Risk Level:** MEDIUM")

    # Look for key risks
    risks = _extract_list_items(content, "risk", max_items=2, max_item_chars=60)
    if risks:
        highlights.append(f"**Key Risks:** {'; '.join(risks)}")

    if highlights:
        return "\n".join(highlights) + "\n\n"

    preview = content[:150].replace("\n", " ").strip()
    return f"*{preview}...*\n\n" if preview else "*Risk assessment completed*\n\n"


# =============================================================================
# Validation Output Formatters
# =============================================================================


def format_validation_output(data: dict) -> str:
    """Format validation JSON output for display.

    Handles the actual validation output structure from claims_extraction,
    three_track_validator, and risk_validator agents.

    Args:
        data: Parsed validation JSON data

    Returns:
        Formatted markdown string
    """
    output = []

    summary = data.get("summary", {})
    claims = data.get("claims", [])

    if summary or claims:
        output.append("### Validation Summary\n")

        # Handle claims_extraction summary (Phase 6A)
        if summary.get("market_claims") is not None or summary.get("total_claims") is not None:
            total = summary.get("total_claims", len(claims))
            market = summary.get("market_claims", 0)
            product = summary.get("product_claims", 0)
            financial = summary.get("financial_claims", 0)
            consistency = summary.get("consistency_claims", 0)

            output.append(f"**Total Claims Extracted:** {total}\n")
            output.append(f"- Market claims: {market}")
            output.append(f"- Product claims: {product}")
            output.append(f"- Financial claims: {financial}")
            output.append(f"- Consistency claims: {consistency}")

        # Handle three_track_validator summary
        elif claims and any(c.get("validation") for c in claims):
            supported = partial = unsupported = contradicted = 0

            for claim in claims:
                validation = claim.get("validation", {})
                if isinstance(validation, dict):
                    track1 = validation.get("track_1_evidence_quality", {})
                    label = track1.get("validation_label", "")
                elif isinstance(validation, str):
                    label = validation
                else:
                    label = ""

                label_lower = label.lower()
                if (
                    "supported" in label_lower
                    and "partial" not in label_lower
                    and "un" not in label_lower
                ):
                    supported += 1
                elif "partial" in label_lower:
                    partial += 1
                elif "contradicted" in label_lower:
                    contradicted += 1
                else:
                    unsupported += 1

            total = len(claims)
            output.append(f"**Total Claims Validated:** {total}\n")
            output.append(f"- Supported: {supported}")
            output.append(f"- Partially supported: {partial}")
            output.append(f"- Unsupported: {unsupported}")
            if contradicted > 0:
                output.append(f"- Contradicted: {contradicted}")

        else:
            total = summary.get("total_claims", len(claims))
            output.append(f"**Total Claims:** {total}\n")

    # Key claims section
    if claims:
        output.append("\n### Key Claims\n")

        for claim in claims[:5]:
            text = claim.get("claim_text", claim.get("text", ""))[:100]
            claim_type = claim.get("claim_type", "")

            validation = claim.get("validation", {})
            if isinstance(validation, dict):
                track1 = validation.get("track_1_evidence_quality", {})
                label = track1.get("validation_label", "")
                label_map = {
                    "supported_by_research": "Supported",
                    "partially_supported": "Partial",
                    "unsupported": "Unsupported",
                    "contradicted_by_research": "Contradicted",
                }
                status = label_map.get(label, label)
            elif isinstance(validation, str):
                status = validation.title()
            else:
                status = claim_type.replace("_", " ").title() if claim_type else "Pending"

            output.append(f"- **{status}:** {text}...")

        if len(claims) > 5:
            output.append(f"\n*...and {len(claims) - 5} more claims*")

    return "\n".join(output)


def format_validation_from_string(agent_name: str, json_string: str) -> str:
    """Format validation output from a JSON string, with fallback extraction.

    Args:
        agent_name: Name of the agent
        json_string: JSON-like string output

    Returns:
        Formatted markdown string
    """
    output = []
    output.append(f"### {agent_name.replace('_', ' ').title()}\n")

    # Try standard JSON parsing first
    data = try_parse_json(json_string)
    if data:
        return output[0] + "\n" + format_validation_output(data)

    # If that failed, try to extract key information using regex
    logger.info(f"Standard JSON parsing failed for {agent_name}, trying regex extraction")

    # Try to count claims
    claims_match = re.search(r'"total_claims"\s*:\s*(\d+)', json_string)
    if claims_match:
        total_claims = claims_match.group(1)
        output.append(f"**Total Claims:** {total_claims}\n")

    # Try to extract claim types
    market_match = re.search(r'"market_claims"\s*:\s*(\d+)', json_string)
    product_match = re.search(r'"product_claims"\s*:\s*(\d+)', json_string)
    financial_match = re.search(r'"financial_claims"\s*:\s*(\d+)', json_string)

    if market_match or product_match or financial_match:
        output.append("**Claim Breakdown:**")
        if market_match:
            output.append(f"- Market claims: {market_match.group(1)}")
        if product_match:
            output.append(f"- Product claims: {product_match.group(1)}")
        if financial_match:
            output.append(f"- Financial claims: {financial_match.group(1)}")
        output.append("")

    # Try to extract validation counts
    supported_match = re.search(r'"supported"\s*:\s*(\d+)', json_string)
    partial_match = re.search(r'"partial"\s*:\s*(\d+)', json_string)
    unsupported_match = re.search(r'"unsupported"\s*:\s*(\d+)', json_string)

    if supported_match or partial_match or unsupported_match:
        output.append("**Validation Results:**")
        if supported_match:
            output.append(f"- Supported: {supported_match.group(1)}")
        if partial_match:
            output.append(f"- Partial: {partial_match.group(1)}")
        if unsupported_match:
            output.append(f"- Unsupported: {unsupported_match.group(1)}")
        output.append("")

    # Try to extract risk counts
    high_risk_match = re.search(r'"high_risks"\s*:\s*(\d+)', json_string)
    medium_risk_match = re.search(r'"medium_risks"\s*:\s*(\d+)', json_string)

    if high_risk_match or medium_risk_match:
        high = high_risk_match.group(1) if high_risk_match else "0"
        medium = medium_risk_match.group(1) if medium_risk_match else "0"
        output.append(f"**Risk Assessment:** {high} high-priority, {medium} medium-priority\n")

    # Try to extract a few claim texts
    claim_texts = re.findall(r'"claim_text"\s*:\s*"([^"]{10,100})', json_string)
    if not claim_texts:
        claim_texts = re.findall(r'"text"\s*:\s*"([^"]{10,100})', json_string)

    if claim_texts:
        output.append("**Sample Claims:**")
        for claim in claim_texts[:5]:
            output.append(f"- {claim}...")
        if len(claim_texts) > 5:
            output.append(f"*... and {len(claim_texts) - 5} more claims*")
        output.append("")

    # If we extracted anything useful, return it
    if len(output) > 1:
        output.append("\n*Full validation data saved to session files.*\n")
        return "\n".join(output) + "\n"

    # Last resort: show a summary message instead of raw JSON
    logger.warning(f"Could not extract validation data for {agent_name}, showing summary")
    return f"### {agent_name.replace('_', ' ').title()}\n\nValidation complete. Full results saved to session files.\n\n"


# =============================================================================
# Stage Content Builder
# =============================================================================


def build_full_stage_content(
    stage_slug: str,
    stage_outputs: dict[str, str],
    stage_description: str = "",
) -> str:
    """Build full content for expanded step view.

    Args:
        stage_slug: Stage slug
        stage_outputs: Dict of agent_name -> output_content
        stage_description: Optional stage description to show at the top

    Returns:
        Full formatted content string
    """
    if not stage_outputs:
        return "*No output available*"

    content_parts = []

    # Add stage description header if provided
    if stage_description:
        content_parts.append(f"*{stage_description}*\n\n---")

    for agent_name, output in stage_outputs.items():
        # Clean agent name for display
        display_name = agent_name.replace("_", " ").title()

        # Clean output content
        clean_output = skip_agent_preamble(output)
        clean_output = strip_thinking_tags(clean_output)

        if clean_output and len(clean_output) > 50:
            content_parts.append(f"### {display_name}\n\n{clean_output}")

    if not content_parts:
        return "*No detailed output available*"

    return "\n\n".join(content_parts)


# =============================================================================
# OutputFormatter Service Class
# =============================================================================

# Stage slug -> extractor function mapping
STAGE_EXTRACTORS: dict[str, Callable[..., str]] = {
    "idea-analysis": extract_concept_highlights,
    "market-context": extract_market_highlights,
    "niche-selection": extract_niche_highlights,
    "product-strategy": extract_strategy_highlights,
    "business-planning": extract_business_highlights,
    "risk-assessment": extract_risk_highlights,
    "validation-summary": extract_validation_highlights,
    "mvp-specification": extract_concept_highlights,  # Similar format
}


class OutputFormatter:
    """Service class for formatting agent outputs.

    Provides a unified interface for all output formatting operations.

    Usage:
        formatter = OutputFormatter()

        # Extract highlights for a stage
        highlights = formatter.extract_highlights("idea-analysis", content)

        # Clean output content
        clean = formatter.clean_output(content)

        # Format validation JSON
        formatted = formatter.format_validation(data)
    """

    def __init__(self, extractors: dict[str, Callable] | None = None):
        """Initialize the formatter.

        Args:
            extractors: Optional custom extractor mapping
        """
        self._extractors = extractors or STAGE_EXTRACTORS

    def extract_highlights(
        self,
        stage_slug: str,
        content: str,
        secondary_content: str = "",
    ) -> str:
        """Extract highlights from stage output.

        Args:
            stage_slug: Stage slug (e.g., "idea-analysis")
            content: Primary content to extract from
            secondary_content: Secondary content (for parallel stages)

        Returns:
            Formatted highlights string
        """
        extractor = self._extractors.get(stage_slug)

        if extractor is None:
            # Fallback: generic preview
            clean = self.clean_output(content)
            preview = clean[:200].replace("\n", " ").strip()
            return f"*{preview}...*\n\n" if preview else "*Stage completed*\n\n"

        # Handle extractors that take multiple content args
        if stage_slug in ("market-context", "niche-selection"):
            return extractor(content, secondary_content)
        return extractor(content)

    def clean_output(self, content: str) -> str:
        """Clean output by removing preamble and thinking tags.

        Args:
            content: Raw output content

        Returns:
            Cleaned content
        """
        content = strip_thinking_tags(content)
        content = skip_agent_preamble(content)
        return content

    def format_validation(self, data: dict) -> str:
        """Format validation data as markdown.

        Args:
            data: Parsed validation JSON

        Returns:
            Formatted markdown string
        """
        return format_validation_output(data)

    def format_validation_string(self, agent_name: str, json_string: str) -> str:
        """Format validation from JSON string with fallback.

        Args:
            agent_name: Name of the agent
            json_string: JSON-like string

        Returns:
            Formatted markdown string
        """
        return format_validation_from_string(agent_name, json_string)

    def build_stage_content(
        self, stage_slug: str, stage_outputs: dict[str, str], stage_description: str = ""
    ) -> str:
        """Build full content for a stage.

        Args:
            stage_slug: Stage slug
            stage_outputs: Dict of agent outputs
            stage_description: Optional stage description to include at top

        Returns:
            Full formatted content
        """
        return build_full_stage_content(stage_slug, stage_outputs, stage_description)

    def try_parse_json(self, content: str) -> dict | None:
        """Try to parse JSON from content.

        Args:
            content: String that may contain JSON

        Returns:
            Parsed dict or None
        """
        return try_parse_json(content)
