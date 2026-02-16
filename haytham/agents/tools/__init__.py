"""Agent tools for Haytham.

This module contains @tool decorated functions that agents can use
to apply consistent business rules during their analysis.

Tools encapsulate domain logic that should be:
- Consistent across all agent invocations
- Testable independently of agent behavior
- Explicit rather than buried in prompts
"""

from .build_buy import (
    estimate_integration_effort,
    evaluate_build_buy_decision,
    search_service_catalog,
)
from .competitor_recording import (
    clear_competitor_accumulator,
    get_competitor_data,
    record_competitor,
    record_market_positioning,
    record_sentiment,
)
from .content_extraction import (
    extract_key_metrics,
    extract_list_items,
    extract_section_content,
    identify_document_sections,
    summarize_for_stage,
)
from .context_retrieval import (
    clear_context_store,
    get_context_by_key,
    get_context_summary,
    list_available_context,
    search_context,
    set_context_store,
)
from .recommendation import (
    clear_scorecard,
    compute_verdict,
    evaluate_recommendation,
    record_counter_signal,
    record_dimension_score,
    record_knockout,
    set_risk_and_evidence,
)
from .risk_classification import classify_risk_level

__all__ = [
    "classify_risk_level",
    "clear_competitor_accumulator",
    "clear_context_store",
    "clear_scorecard",
    "compute_verdict",
    "estimate_integration_effort",
    "evaluate_build_buy_decision",
    "evaluate_recommendation",
    "get_competitor_data",
    "extract_key_metrics",
    "extract_list_items",
    "extract_section_content",
    "get_context_by_key",
    "get_context_summary",
    "identify_document_sections",
    "list_available_context",
    "record_competitor",
    "record_counter_signal",
    "record_dimension_score",
    "record_knockout",
    "record_market_positioning",
    "record_sentiment",
    "search_context",
    "search_service_catalog",
    "set_context_store",
    "set_risk_and_evidence",
    "summarize_for_stage",
]
