"""Tests for JTBD section extraction from market intelligence output."""

from haytham.workflow.stages.idea_validation import _extract_jtbd_section

SAMPLE_MI_OUTPUT = """\
### 1. Market Context Summary

- **Primary Category:** Online mental health platforms
- **Adjacent Categories:** Telehealth, community wellness
- **Target Segment:** Adults seeking peer support groups

### 2. Jobs-to-be-Done Analysis

**A. Core Jobs (customer perspective)**
- Help me find a peer support group that fits my schedule and comfort level
- Help me connect with people who share my specific challenges

**B. Job Dimensions**
- Functional: Match with a compatible support group quickly
- Emotional: Feel safe and understood in a group setting
- Social: Be part of a community without stigma

**C. Current Solutions**
- Local 12-step programs (limited scheduling, no filtering)
- Reddit communities (anonymous but unstructured)
- Meetup groups (broad, not mental-health focused)

### 3. Market Size

- **Relevant Market:** Peer support platforms — est. $2.1B [estimate]
- **Bottom-up:** 40M US adults seeking support x $50/yr = $2B TAM

### 4. Market Trends

1. Trend one
2. Trend two
3. Trend three
"""


class TestExtractJtbdSection:
    """Test _extract_jtbd_section helper."""

    def test_extracts_jtbd_from_standard_output(self):
        """Should extract the full JTBD section between headings."""
        result = _extract_jtbd_section(SAMPLE_MI_OUTPUT)
        assert "Core Jobs (customer perspective)" in result
        assert "Help me find a peer support group" in result
        assert "Job Dimensions" in result
        assert "Current Solutions" in result
        # Should NOT include content from other sections
        assert "Market Context Summary" not in result
        assert "Market Size" not in result

    def test_returns_empty_string_when_no_jtbd_section(self):
        """Should return empty string when JTBD section is missing."""
        output_without_jtbd = """\
### 1. Market Context Summary

Some market context here.

### 3. Market Size

Some market size data.
"""
        result = _extract_jtbd_section(output_without_jtbd)
        assert result == ""

    def test_returns_empty_string_for_empty_input(self):
        """Should return empty string for empty input."""
        assert _extract_jtbd_section("") == ""

    def test_handles_jtbd_as_last_section(self):
        """Should extract JTBD when it's the last section (no trailing ###)."""
        output = """\
### 1. Market Context Summary

Some context.

### 2. Jobs-to-be-Done Analysis

- Help me do the thing
- Functional: Complete the task
"""
        result = _extract_jtbd_section(output)
        assert "Help me do the thing" in result
        assert "Functional: Complete the task" in result

    def test_handles_varied_heading_spacing(self):
        """Should handle spacing variants in the heading."""
        output = """\
###  2.  Jobs-to-be-Done Analysis

- Core job content here
- More content

### 3. Next Section
"""
        result = _extract_jtbd_section(output)
        assert "Core job content here" in result

    def test_does_not_include_heading_itself(self):
        """The extracted section should not include the heading line."""
        result = _extract_jtbd_section(SAMPLE_MI_OUTPUT)
        assert "### 2. Jobs-to-be-Done Analysis" not in result
