"""Tests for web_search domain filtering logic."""

import importlib


def _import_web_search():
    """Import web_search module."""
    return importlib.import_module("haytham.agents.utils.web_search")


class TestApplyDomainFilter:
    """Test _apply_domain_filter helper."""

    def test_no_domains_returns_original_query(self):
        mod = _import_web_search()
        assert mod._apply_domain_filter("test query", None) == "test query"

    def test_empty_list_returns_original_query(self):
        mod = _import_web_search()
        assert mod._apply_domain_filter("test query", []) == "test query"

    def test_single_domain_adds_site_prefix(self):
        mod = _import_web_search()
        result = mod._apply_domain_filter("competitor pricing", ["g2.com"])
        assert result == "site:g2.com competitor pricing"

    def test_multiple_domains_or_joined(self):
        mod = _import_web_search()
        result = mod._apply_domain_filter("reviews", ["g2.com", "capterra.com"])
        assert result == "site:g2.com OR site:capterra.com reviews"

    def test_three_domains(self):
        mod = _import_web_search()
        result = mod._apply_domain_filter("test", ["a.com", "b.com", "c.com"])
        assert "site:a.com" in result
        assert "site:b.com" in result
        assert "site:c.com" in result
        assert result.endswith(" test")
