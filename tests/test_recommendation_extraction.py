"""Tests for _extract_recommendation 3-tier fallback (C3 fix).

Covers:
- Tier 1: Recommendation from Burr state
- Tier 2: Recommendation from recommendation.json on disk
- Tier 3: Anchored regex on validation-summary output
- Fallback to None when no recommendation found
"""

import json
from unittest.mock import MagicMock

import pytest

from haytham.workflow.burr_workflow import _extract_recommendation


def _make_state(data: dict) -> MagicMock:
    """Create a mock Burr State with dict-like .get()."""
    state = MagicMock()
    state.get = lambda key, default=None: data.get(key, default)
    return state


class TestTier1BurrState:
    """Tier 1: recommendation from Burr state."""

    def test_go_from_state(self):
        state = _make_state({"recommendation": "GO"})
        assert _extract_recommendation(state, {}, None) == "GO"

    def test_nogo_from_state(self):
        state = _make_state({"recommendation": "NO-GO"})
        assert _extract_recommendation(state, {}, None) == "NO-GO"

    def test_pivot_from_state(self):
        state = _make_state({"recommendation": "PIVOT"})
        assert _extract_recommendation(state, {}, None) == "PIVOT"

    def test_invalid_value_falls_through(self):
        """Invalid recommendation in state does not match tier 1."""
        state = _make_state({"recommendation": "MAYBE"})
        assert _extract_recommendation(state, {}, None) is None


class TestTier2DiskFile:
    """Tier 2: recommendation from recommendation.json."""

    def test_reads_from_disk(self, tmp_path):
        meta_path = tmp_path / "recommendation.json"
        meta_path.write_text(json.dumps({"recommendation": "PIVOT"}))

        sm = MagicMock()
        sm.session_dir = tmp_path

        state = _make_state({})
        assert _extract_recommendation(state, {}, sm) == "PIVOT"

    def test_skips_when_no_file(self, tmp_path):
        sm = MagicMock()
        sm.session_dir = tmp_path

        state = _make_state({})
        assert _extract_recommendation(state, {}, sm) is None

    def test_skips_when_corrupted(self, tmp_path):
        meta_path = tmp_path / "recommendation.json"
        meta_path.write_text("not json")

        sm = MagicMock()
        sm.session_dir = tmp_path

        state = _make_state({})
        assert _extract_recommendation(state, {}, sm) is None


class TestTier3Regex:
    """Tier 3: anchored regex on validation-summary output."""

    def test_extracts_from_dict_result(self):
        """Extracts recommendation from the standard _extract_results dict format."""
        results = {
            "validation-summary": {
                "status": "completed",
                "outputs": {
                    "report_synthesis": "## Summary\nRECOMMENDATION: GO\nSome other text."
                },
            }
        }
        state = _make_state({})
        assert _extract_recommendation(state, results, None) == "GO"

    def test_extracts_nogo(self):
        results = {
            "validation-summary": {
                "status": "completed",
                "outputs": {"report_synthesis": "RECOMMENDATION: NO-GO"},
            }
        }
        state = _make_state({})
        assert _extract_recommendation(state, results, None) == "NO-GO"

    def test_no_match_returns_none(self):
        results = {
            "validation-summary": {
                "status": "completed",
                "outputs": {"report_synthesis": "No recommendation here."},
            }
        }
        state = _make_state({})
        assert _extract_recommendation(state, results, None) is None

    def test_underscore_key_does_not_match(self):
        """The old underscore key 'validation_summary' should NOT work (bug was here)."""
        results = {
            "validation_summary": {
                "status": "completed",
                "outputs": {"report_synthesis": "RECOMMENDATION: GO"},
            }
        }
        state = _make_state({})
        assert _extract_recommendation(state, results, None) is None


class TestTierPriority:
    """Tier 1 takes precedence over tier 2 and 3."""

    def test_state_wins_over_disk(self, tmp_path):
        meta_path = tmp_path / "recommendation.json"
        meta_path.write_text(json.dumps({"recommendation": "PIVOT"}))

        sm = MagicMock()
        sm.session_dir = tmp_path

        state = _make_state({"recommendation": "GO"})
        assert _extract_recommendation(state, {}, sm) == "GO"

    def test_disk_wins_over_regex(self, tmp_path):
        meta_path = tmp_path / "recommendation.json"
        meta_path.write_text(json.dumps({"recommendation": "NO-GO"}))

        sm = MagicMock()
        sm.session_dir = tmp_path

        results = {
            "validation-summary": {
                "status": "completed",
                "outputs": {"report_synthesis": "RECOMMENDATION: GO"},
            }
        }
        state = _make_state({})
        assert _extract_recommendation(state, results, sm) == "NO-GO"
