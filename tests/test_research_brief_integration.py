"""Tests for research_brief data flow into report_synthesis."""

from unittest.mock import MagicMock, patch

from haytham.workflow.stages.idea_validation import run_report_synthesis
from haytham.workflow.validators.report_guardrails import validate_no_judgment_language


class TestReportSynthesisReadsResearchBrief:
    """Verify report_synthesis reads research_brief, not raw upstream data."""

    @patch("haytham.workflow.stages.idea_validation.run_agent")
    def test_query_contains_research_brief(self, mock_run_agent):
        """Report synthesis query should embed the research_brief content."""
        mock_run_agent.return_value = {
            "output": '{"recommendation": "GO", "executive_summary": {}, "report": "test"}',
            "status": "completed",
        }

        state = MagicMock()
        state.get.side_effect = lambda key, default="": {
            "system_goal": "A fitness app",
            "research_brief": "## Our Understanding\nFitness tracking\n## What We Found\nTAM: $5B",
            "idea_analysis": "old idea analysis that should NOT appear",
            "market_context": "old market context that should NOT appear",
            "session_manager": MagicMock(),
            "concept_anchor_str": "",
            "concept_anchor": None,
        }.get(key, default)

        run_report_synthesis(state)

        call_args = mock_run_agent.call_args
        query = call_args[0][1]  # Second positional arg is query

        assert "Research Brief" in query
        assert "old idea analysis that should NOT appear" not in query
        assert "old market context that should NOT appear" not in query


class TestJudgmentLanguageValidator:
    """Verify the research brief post-validator catches opinion language."""

    def test_clean_brief_returns_no_warnings(self):
        output = "## Our Understanding\nA fitness app.\n## What We Found\nTAM: $5B [from Statista]"
        warnings = validate_no_judgment_language(output, None)
        assert warnings == []

    def test_catches_judgment_words(self):
        output = "This is a promising market with strong growth potential."
        warnings = validate_no_judgment_language(output, None)
        assert len(warnings) > 0
        assert any("promising" in w.lower() or "strong" in w.lower() for w in warnings)

    def test_catches_recommendation_language(self):
        output = "We recommend focusing on the enterprise segment."
        warnings = validate_no_judgment_language(output, None)
        assert len(warnings) > 0

    def test_ignores_judgment_words_in_section_headers(self):
        """Words in headers like 'What We Couldn't Verify' should not trigger."""
        output = "## What We Couldn't Verify\nPricing data not found for 3 competitors."
        warnings = validate_no_judgment_language(output, None)
        assert warnings == []
