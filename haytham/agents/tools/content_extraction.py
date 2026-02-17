"""Content extraction tools for summarizing agent outputs.

These tools allow an agent to analyze and extract key information
from stage outputs, replacing hardcoded keyword matching with
tool-based extraction that can be reasoned about.
"""

import json
import re

from strands import tool

# Max line length to treat as a colon-based section header (e.g. "Problem:")
_HEADER_MAX_LEN = 60


@tool
def identify_document_sections(content: str) -> str:
    """Identify the sections and structure of a document.

    Use this tool to understand what sections exist in a document
    before deciding what to extract. Returns section headers with
    their line numbers and estimated content length.

    Args:
        content: The document content to analyze

    Returns:
        JSON with list of sections found, including headers and content previews
    """
    lines = content.split("\n")
    sections = []
    current_section = None

    for i, line in enumerate(lines):
        # Detect markdown headers
        if line.startswith("#"):
            # Save previous section
            if current_section:
                current_section["end_line"] = i - 1
                current_section["line_count"] = i - current_section["start_line"]
                sections.append(current_section)

            # Start new section
            level = len(re.match(r"^#+", line).group())
            title = line.lstrip("#").strip()
            current_section = {
                "level": level,
                "title": title,
                "start_line": i,
                "preview": "",
            }

        # Detect colon-based headers (e.g., "Problem:" or "Solution:")
        elif ":" in line and len(line) < _HEADER_MAX_LEN and not line.startswith("-"):
            potential_header = line.split(":")[0].strip()
            if potential_header and potential_header[0].isupper():
                if current_section:
                    current_section["end_line"] = i - 1
                    current_section["line_count"] = i - current_section["start_line"]
                    sections.append(current_section)

                current_section = {
                    "level": 3,  # Treat as h3 equivalent
                    "title": potential_header,
                    "start_line": i,
                    "preview": line.split(":", 1)[1].strip()[:100] if ":" in line else "",
                }

        # Add preview from first content line
        elif current_section and not current_section.get("preview") and line.strip():
            current_section["preview"] = line.strip()[:100]

    # Don't forget last section
    if current_section:
        current_section["end_line"] = len(lines) - 1
        current_section["line_count"] = len(lines) - current_section["start_line"]
        sections.append(current_section)

    return json.dumps(
        {
            "total_lines": len(lines),
            "sections_found": len(sections),
            "sections": sections,
        },
        indent=2,
    )


@tool
def extract_section_content(
    content: str,
    section_keywords: str,
    max_lines: int = 10,
    include_lists: bool = True,
) -> str:
    """Extract content from a section matching the given keywords.

    Use this tool to extract content from a specific section of a document.
    Provide keywords that might appear in the section header.

    Args:
        content: The full document content
        section_keywords: Comma-separated keywords to match in section headers
                         (e.g., "problem,challenge,issue" or "solution,approach")
        max_lines: Maximum lines to extract from the section
        include_lists: Whether to include bullet point lists

    Returns:
        JSON with extracted content, or indication that section was not found
    """
    keywords = [k.strip().lower() for k in section_keywords.split(",")]
    lines = content.split("\n")
    extracted = []
    found_section = None

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Check if this line is a header matching our keywords
        is_header = line.startswith("#") or (":" in line and len(line) < _HEADER_MAX_LEN)
        if is_header and any(kw in line_lower for kw in keywords):
            found_section = line.strip()
            # Extract following content
            for j in range(i + 1, min(i + max_lines + 1, len(lines))):
                next_line = lines[j].strip()

                # Stop at next header
                if next_line.startswith("#"):
                    break

                # Handle bullet points
                if next_line.startswith("-") or next_line.startswith("*"):
                    if include_lists:
                        extracted.append(next_line.lstrip("-*").strip())
                elif next_line:
                    extracted.append(next_line)

            break

    if found_section:
        return json.dumps(
            {
                "found": True,
                "section_header": found_section,
                "content": extracted,
                "summary": " ".join(extracted)[:300],
            },
            indent=2,
        )
    else:
        return json.dumps(
            {
                "found": False,
                "searched_keywords": keywords,
                "suggestion": "Try different keywords or check document structure first",
            },
            indent=2,
        )


@tool
def extract_key_metrics(content: str) -> str:
    """Extract key metrics and numbers from content.

    Use this tool to find quantitative data like market sizes,
    percentages, dollar amounts, and other metrics.

    Args:
        content: The content to analyze

    Returns:
        JSON with extracted metrics categorized by type
    """
    metrics = {
        "currency": [],
        "percentages": [],
        "counts": [],
        "time_estimates": [],
    }

    # Currency patterns ($X, $X billion/million, etc.)
    currency_pattern = r"\$[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|B|M|k|K))?"
    for match in re.finditer(currency_pattern, content, re.IGNORECASE):
        context_start = max(0, match.start() - 30)
        context_end = min(len(content), match.end() + 30)
        context = content[context_start:context_end].replace("\n", " ").strip()
        metrics["currency"].append(
            {
                "value": match.group(),
                "context": f"...{context}...",
            }
        )

    # Percentage patterns
    pct_pattern = r"\d+(?:\.\d+)?%"
    for match in re.finditer(pct_pattern, content):
        context_start = max(0, match.start() - 30)
        context_end = min(len(content), match.end() + 30)
        context = content[context_start:context_end].replace("\n", " ").strip()
        metrics["percentages"].append(
            {
                "value": match.group(),
                "context": f"...{context}...",
            }
        )

    # Time estimates (hours, days, weeks)
    time_pattern = r"\d+(?:-\d+)?\s*(?:hour|day|week|month|year)s?"
    for match in re.finditer(time_pattern, content, re.IGNORECASE):
        metrics["time_estimates"].append(match.group())

    # Counts with context (X users, X customers, etc.)
    count_pattern = r"(\d+(?:,\d{3})*(?:\+)?)\s+(user|customer|client|company|startup|business)"
    for match in re.finditer(count_pattern, content, re.IGNORECASE):
        metrics["counts"].append(f"{match.group(1)} {match.group(2)}s")

    return json.dumps(
        {
            "metrics_found": sum(len(v) for v in metrics.values()),
            "metrics": metrics,
        },
        indent=2,
    )


@tool
def extract_list_items(
    content: str,
    section_keywords: str,
    max_items: int = 5,
) -> str:
    """Extract bullet point items from a section.

    Use this tool to get list items from sections like
    "Key Features", "Risks", "Recommendations", etc.

    Args:
        content: The full document content
        section_keywords: Comma-separated keywords for section matching
        max_items: Maximum number of items to extract

    Returns:
        JSON with list items and their context
    """
    keywords = [k.strip().lower() for k in section_keywords.split(",")]
    lines = content.split("\n")
    items = []
    in_section = False

    for line in lines:
        line_lower = line.lower()

        # Check for section header
        if any(kw in line_lower for kw in keywords) and ("#" in line or ":" in line):
            in_section = True
            continue

        # Extract items from section
        if in_section:
            # Stop at next header
            if line.startswith("#") or (
                line.strip() and ":" in line and len(line) < _HEADER_MAX_LEN
            ):
                if items:
                    break
                in_section = False
                continue

            # Extract bullet items
            if line.strip().startswith(("-", "*", "•")):
                item = line.strip().lstrip("-*•").strip()
                if item and len(item) > 5:
                    items.append(item)
                    if len(items) >= max_items:
                        break

    return json.dumps(
        {
            "found": len(items) > 0,
            "searched_keywords": keywords,
            "items_count": len(items),
            "items": items,
        },
        indent=2,
    )


@tool
def summarize_for_stage(content: str, stage_type: str) -> str:
    """Generate a summary appropriate for a specific stage type.

    Use this tool to get a structured summary tailored to the stage.
    The tool knows what information is most relevant for each stage type.

    Args:
        content: The content to summarize
        stage_type: One of: "idea_analysis", "market_research", "risk_assessment",
                    "validation", "mvp_spec", "business_plan"

    Returns:
        JSON with structured highlights appropriate for the stage type
    """
    highlights = {}

    stage_configs = {
        "idea_analysis": {
            "sections": ["problem", "solution", "target,audience,user,customer"],
            "labels": ["Problem", "Solution", "Target Audience"],
        },
        "market_research": {
            "sections": ["market size,tam,sam", "segment,customer", "trend,growth", "opportunity"],
            "labels": ["Market Size", "Segments", "Trends", "Opportunities"],
        },
        "risk_assessment": {
            "sections": [
                "risk level,overall risk",
                "risk,threat,challenge",
                "mitigation,recommendation",
            ],
            "labels": ["Risk Level", "Key Risks", "Mitigations"],
        },
        "validation": {
            "sections": [
                "summary,overview",
                "supported,validated",
                "unsupported,failed",
                "recommendation",
            ],
            "labels": ["Summary", "Validated", "Concerns", "Recommendation"],
        },
        "mvp_spec": {
            "sections": ["feature,capability", "scope,boundary", "success,criteria,metric"],
            "labels": ["Features", "Scope", "Success Criteria"],
        },
        "business_plan": {
            "sections": ["revenue,pricing,monetization", "cost,expense", "timeline,milestone"],
            "labels": ["Revenue Model", "Costs", "Timeline"],
        },
    }

    config = stage_configs.get(
        stage_type,
        {
            "sections": ["summary,overview"],
            "labels": ["Summary"],
        },
    )

    lines = content.split("\n")

    for section_kw, label in zip(config["sections"], config["labels"], strict=True):
        keywords = [k.strip().lower() for k in section_kw.split(",")]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords) and ("#" in line or ":" in line):
                # Extract content
                extracted = []
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith("#"):
                        break
                    if next_line.startswith(("-", "*")):
                        extracted.append(next_line.lstrip("-*").strip())
                    elif next_line and len(next_line) > 10:
                        extracted.append(next_line)

                if extracted:
                    highlights[label] = extracted[0] if len(extracted) == 1 else extracted[:3]
                break

    # Fallback if nothing found
    if not highlights:
        # Get first meaningful paragraph
        for line in lines:
            clean = line.strip()
            if clean and not clean.startswith("#") and len(clean) > 50:
                highlights["Summary"] = clean[:200]
                break

    return json.dumps(
        {
            "stage_type": stage_type,
            "highlights_found": len(highlights),
            "highlights": highlights,
        },
        indent=2,
    )
