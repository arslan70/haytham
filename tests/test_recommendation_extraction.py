"""Tests for _extract_recommendation 2-tier fallback (ADR-026).

Covers:
- Tier 1: Recommendation from Burr state
- Tier 2: Recommendation from recommendation.json on disk
- Fallback to None when no recommendation found
"""

import json
from unittest.mock import MagicMock

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


class TestNoRegexFallback:
    """Tier 3 regex fallback was removed in ADR-026. Results dict is ignored."""

    def test_results_dict_ignored(self):
        """Results dict with recommendation text does NOT match (no regex tier)."""
        results = {
            "report-synthesis": {
                "status": "completed",
                "outputs": {"report_synthesis": "RECOMMENDATION: GO"},
            }
        }
        state = _make_state({})
        assert _extract_recommendation(state, results, None) is None

    def test_returns_none_without_state_or_disk(self):
        state = _make_state({})
        assert _extract_recommendation(state, {}, None) is None


class TestTierPriority:
    """Tier 1 takes precedence over tier 2."""

    def test_state_wins_over_disk(self, tmp_path):
        meta_path = tmp_path / "recommendation.json"
        meta_path.write_text(json.dumps({"recommendation": "PIVOT"}))

        sm = MagicMock()
        sm.session_dir = tmp_path

        state = _make_state({"recommendation": "GO"})
        assert _extract_recommendation(state, {}, sm) == "GO"
