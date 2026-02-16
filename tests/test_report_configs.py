"""Tests for report_configs helpers."""

import re

from haytham.agents.tools.report_configs import _MI_OVERLAP_KEYWORDS, _strip_sections


class TestStripSections:
    """Verify _strip_sections removes duplicate content by keyword pattern."""

    def test_removes_h2_competitor_analysis(self):
        text = (
            "## Market Size\n\nThe market is large.\n\n"
            "## Competitor Analysis\n\nCompetitor A does X.\nCompetitor B does Y.\n\n"
            "## Key Trends\n\nTrend data here."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "## Key Trends" in result
        assert "Competitor A" not in result
        assert "Competitor B" not in result

    def test_removes_h3_competitive_positioning(self):
        text = (
            "## Market Size\n\nThe market is large.\n\n"
            "### Competitive Positioning\n\nPositioning details.\n\n"
            "## Key Trends\n\nTrend data here."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "## Key Trends" in result
        assert "Competitive Positioning" not in result
        assert "Positioning details" not in result

    def test_removes_h3_competitor_identification(self):
        text = (
            "## Market Size\n\nMarket data.\n\n"
            "### Competitor Identification\n\nList of competitors.\n\n"
            "### Growth Drivers\n\nGrowth info."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "### Growth Drivers" in result
        assert "Competitor Identification" not in result

    def test_preserves_non_competitor_content(self):
        text = "## Market Size\n\nThe TAM is $5B.\n\n## Growth Trends\n\nGrowing at 15% CAGR."
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert result == text

    def test_handles_competitor_section_at_end(self):
        text = "## Market Size\n\nMarket data.\n\n## Competitor Analysis\n\nCompetitor data at end."
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "Market data" in result
        assert "Competitor" not in result

    def test_returns_empty_string_when_all_content_is_competitor(self):
        text = "## Competitive Landscape\n\nAll content is competitors."
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert result == ""

    def test_nested_h3_under_competitor_h2_removed(self):
        text = (
            "## Market Size\n\nData.\n\n"
            "## Competitor Analysis\n\nIntro.\n\n"
            "### Direct Competitors\n\nDirect list.\n\n"
            "### Indirect Competitors\n\nIndirect list.\n\n"
            "## Key Trends\n\nTrends."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "## Key Trends" in result
        assert "Direct Competitors" not in result
        assert "Indirect Competitors" not in result
        assert "Competitor Analysis" not in result

    def test_case_insensitive_keyword_match(self):
        text = (
            "## Market Size\n\nData.\n\n## COMPETITOR Overview\n\nOverview.\n\n## Trends\n\nTrends."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "## Trends" in result
        assert "COMPETITOR" not in result

    # --- New overlap coverage ---

    def test_removes_opportunities_section(self):
        """MI 'Opportunities and Threats' heading is stripped."""
        text = (
            "## Market Size\n\nData.\n\n"
            "## Opportunities and Threats\n\nDuplicate content.\n\n"
            "## Market Trends\n\nTrends."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "## Market Trends" in result
        assert "Opportunities and Threats" not in result

    def test_removes_switching_section(self):
        """MI switching-related heading is stripped."""
        text = (
            "## Market Size\n\nData.\n\n"
            "### Switching Costs\n\nHigh lock-in.\n\n"
            "## Market Trends\n\nTrends."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "## Market Trends" in result
        assert "Switching Costs" not in result
        assert "High lock-in" not in result

    def test_removes_sentiment_section(self):
        """MI sentiment-related heading is stripped."""
        text = (
            "## Market Size\n\nData.\n\n"
            "### User Sentiment\n\nFrustrations and quotes.\n\n"
            "## Market Trends\n\nTrends."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Size" in result
        assert "## Market Trends" in result
        assert "User Sentiment" not in result
        assert "Frustrations" not in result

    def test_preserves_market_risks_section(self):
        """New MI Section 5 'Market Risks' must NOT be stripped."""
        text = (
            "## Market Size\n\nData.\n\n"
            "## Market Risks\n\nRegulatory barriers.\n\n"
            "## Market Trends\n\nTrends."
        )
        result = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
        assert "## Market Risks" in result
        assert "Regulatory barriers" in result

    def test_custom_keyword_pattern(self):
        """_strip_sections works with arbitrary keyword patterns."""
        custom = re.compile(r"alpha|beta", re.IGNORECASE)
        text = (
            "## Introduction\n\nIntro text.\n\n"
            "## Alpha Features\n\nAlpha content.\n\n"
            "## Beta Features\n\nBeta content.\n\n"
            "## Stable Features\n\nStable content."
        )
        result = _strip_sections(text, custom)
        assert "## Introduction" in result
        assert "## Stable Features" in result
        assert "Alpha Features" not in result
        assert "Beta Features" not in result

    def test_strips_lean_canvas_from_concept_expansion(self):
        """CE strip pattern removes Lean Canvas and Concept Health sections."""
        from haytham.agents.tools.report_configs import _CE_STRIP_KEYWORDS

        text = (
            "## Problem Analysis\n\nProblem details.\n\n"
            "## Lean Canvas\n\nCanvas content.\n\n"
            "## Concept Health\n\nHealth signals.\n\n"
            "## User Personas\n\nPersona details."
        )
        result = _strip_sections(text, _CE_STRIP_KEYWORDS)
        assert "## Problem Analysis" in result
        assert "## User Personas" in result
        assert "Lean Canvas" not in result
        assert "Concept Health" not in result
