"""Output Formatting Services for Haytham.

This package provides centralized output formatting, content extraction,
and parsing utilities.

Usage:
    from haytham.formatters import OutputFormatter

    formatter = OutputFormatter()
    highlights = formatter.extract_highlights("idea-analysis", content)
"""

from .output_formatter import (
    AGENT_PREAMBLE_PATTERNS,
    # Constants
    STAGE_EXTRACTORS,
    # Service class
    OutputFormatter,
    build_full_stage_content,
    extract_business_highlights,
    # Content extractors
    extract_concept_highlights,
    extract_market_highlights,
    extract_niche_highlights,
    extract_risk_highlights,
    extract_strategy_highlights,
    extract_validation_highlights,
    format_validation_from_string,
    # Formatters
    format_validation_output,
    skip_agent_preamble,
    # Utility functions
    strip_thinking_tags,
    try_parse_json,
)

__all__ = [
    "OutputFormatter",
    "strip_thinking_tags",
    "skip_agent_preamble",
    "try_parse_json",
    "extract_concept_highlights",
    "extract_market_highlights",
    "extract_niche_highlights",
    "extract_strategy_highlights",
    "extract_business_highlights",
    "extract_validation_highlights",
    "extract_risk_highlights",
    "format_validation_output",
    "format_validation_from_string",
    "build_full_stage_content",
    "STAGE_EXTRACTORS",
    "AGENT_PREAMBLE_PATTERNS",
]
