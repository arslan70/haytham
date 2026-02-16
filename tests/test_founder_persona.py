"""Tests for FounderPersona dataclass."""

import pytest

from haytham.workflow.anchor_schema import FounderPersona


class TestFounderPersona:
    def test_defaults(self):
        """Default persona has all expected fields."""
        fp = FounderPersona()
        assert fp.age_range == "30-40"
        assert "Solo founder" in fp.team
        assert "bootstrapping" in fp.capital
        assert "Unknown" in fp.domain_expertise

    def test_frozen(self):
        """Persona is immutable."""
        fp = FounderPersona()
        with pytest.raises(AttributeError):
            fp.age_range = "20-30"  # type: ignore[misc]

    def test_to_context_format(self):
        """to_context() produces well-structured markdown."""
        fp = FounderPersona()
        ctx = fp.to_context()
        assert ctx.startswith("## Founder Context")
        assert "- **Age range:** 30-40" in ctx
        assert "- **Team:** Solo founder" in ctx
        assert "- **Capital:**" in ctx
        assert "- **Domain expertise:** Unknown" in ctx
        assert "- **Risk appetite:**" in ctx
        assert "- **Time commitment:**" in ctx
        assert "- **Technical literacy:**" in ctx

    def test_custom_values(self):
        """Custom persona values are reflected in context."""
        fp = FounderPersona(
            domain_expertise="10 years in fintech",
            team="2 co-founders with complementary skills",
        )
        ctx = fp.to_context()
        assert "10 years in fintech" in ctx
        assert "2 co-founders" in ctx
