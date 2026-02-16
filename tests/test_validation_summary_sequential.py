"""Tests for the scorer+narrator split of validation summary.

Covers:
- ScorerOutput / NarrativeFields model validation and round-trips
- merge_scorer_narrator() deterministic merge function
- run_validation_summary_sequential() orchestrator with mocked agents
"""

import json
from unittest import mock

from haytham.agents.worker_validation_summary.validation_summary_models import (
    NarrativeFields,
    ScorerOutput,
    ValidationSummaryOutput,
    _fix_exec_summary_verdict,
    merge_scorer_narrator,
)

# =============================================================================
# Fixtures — minimal valid dicts for scorer and narrator outputs
# =============================================================================


def _scorer_dict(**overrides) -> dict:
    """Build a minimal valid ScorerOutput dict."""
    base = {
        "knockout_criteria": [
            {"criterion": "Problem Reality", "result": "PASS", "evidence": "Confirmed"},
            {"criterion": "Channel Access", "result": "PASS", "evidence": "Online channels"},
            {"criterion": "Regulatory/Ethical", "result": "PASS", "evidence": "No blockers"},
        ],
        "counter_signals": [
            {
                "signal": "Limited external validation",
                "source": "risk_assessment",
                "affected_dimensions": ["Market Opportunity"],
                "evidence_cited": "3 funded competitors validate market",
                "why_score_holds": "Score already conservative at 3",
                "what_would_change_score": "If TAM < $10M, drops to 2",
            },
        ],
        "scorecard": [
            {"dimension": "Problem Severity", "score": 4, "evidence": "Users pay today"},
            {"dimension": "Market Opportunity", "score": 3, "evidence": "Moderate TAM"},
            {"dimension": "Competitive Differentiation", "score": 3, "evidence": "Some moat"},
            {"dimension": "Solution Feasibility", "score": 4, "evidence": "Known tech"},
            {"dimension": "Revenue Viability", "score": 3, "evidence": "Freemium model"},
            {"dimension": "Founder-Market Fit", "score": 3, "evidence": "Relevant exp"},
            {"dimension": "Operational Feasibility", "score": 4, "evidence": "No constraints"},
            {"dimension": "Adoption & Engagement Risk", "score": 3, "evidence": "Moderate change"},
        ],
        "composite_score": 3.4,
        "verdict": "CONDITIONAL GO",
        "recommendation": "GO",
        "confidence_hint": "MEDIUM",
        "floor_capped": False,
        "risk_capped": False,
        "critical_gaps": [],
        "guidance": "Proceed with caution, validate revenue model early.",
        "risk_level": "MEDIUM",
    }
    base.update(overrides)
    return base


def _narrator_dict(**overrides) -> dict:
    """Build a minimal valid NarrativeFields dict."""
    base = {
        "executive_summary": (
            "A SaaS tool for team scheduling validated with moderate evidence. "
            "GO recommendation with MEDIUM confidence."
        ),
        "lean_canvas": {
            "problems": ["Manual scheduling wastes 5+ hours/week", "No team visibility"],
            "customer_segments": ["SMB managers", "Remote teams"],
            "unique_value_proposition": "AI-powered scheduling that learns team preferences",
            "solution": ["Smart calendar sync", "Availability matching", "One-click booking"],
            "revenue_model": "Freemium with $12/user/month Pro tier",
        },
        "validation_findings": {
            "market_opportunity": "$4.2B scheduling market growing 12% YoY",
            "competition": "Incumbents lack AI features; gap in team-first scheduling",
            "critical_risks": [
                "Revenue model unproven (MEDIUM)",
                "Switching cost from existing tools (MEDIUM)",
            ],
        },
        "next_steps": [
            "Conduct 10 user interviews to validate WTP",
            "Build calendar sync MVP in 4 weeks",
            "Track activation rate and weekly retention",
        ],
    }
    base.update(overrides)
    return base


# =============================================================================
# Model validation tests
# =============================================================================


class TestScorerOutputModel:
    def test_round_trip(self):
        data = _scorer_dict()
        model = ScorerOutput.model_validate(data)
        assert model.composite_score == 3.4
        assert model.recommendation == "GO"
        assert len(model.scorecard) == 8
        # Round-trip through JSON
        reparsed = ScorerOutput.model_validate_json(model.model_dump_json())
        assert reparsed.composite_score == model.composite_score

    def test_defaults(self):
        """Defaults for optional fields."""
        data = _scorer_dict()
        del data["confidence_hint"]
        del data["floor_capped"]
        del data["risk_capped"]
        del data["risk_level"]
        model = ScorerOutput.model_validate(data)
        assert model.confidence_hint == ""
        assert model.floor_capped is False
        assert model.risk_capped is False
        assert model.risk_level == "MEDIUM"


class TestNarrativeFieldsModel:
    def test_round_trip(self):
        data = _narrator_dict()
        model = NarrativeFields.model_validate(data)
        assert "scheduling" in model.executive_summary.lower()
        assert len(model.next_steps) == 3
        # Round-trip through JSON
        reparsed = NarrativeFields.model_validate_json(model.model_dump_json())
        assert reparsed.executive_summary == model.executive_summary


# =============================================================================
# Merge function tests
# =============================================================================


class TestMergeScorerNarrator:
    def test_happy_path(self):
        """Merge produces a valid ValidationSummaryOutput dict."""
        merged = merge_scorer_narrator(_scorer_dict(), _narrator_dict())
        # Should validate as ValidationSummaryOutput
        model = ValidationSummaryOutput.model_validate(merged)
        assert model.recommendation == "GO"
        assert model.go_no_go_assessment.composite_score == 3.4

    def test_preserves_scorer_fields(self):
        """Analytical fields from scorer copied verbatim."""
        scorer = _scorer_dict(floor_capped=True, critical_gaps=["Revenue Viability"])
        merged = merge_scorer_narrator(scorer, _narrator_dict())
        assert merged["go_no_go_assessment"]["floor_capped"] is True
        assert merged["go_no_go_assessment"]["critical_gaps"] == ["Revenue Viability"]
        assert merged["recommendation"] == "GO"
        assert merged["go_no_go_assessment"]["verdict"] == "CONDITIONAL GO"

    def test_preserves_narrator_fields(self):
        """Narrative fields from narrator copied (exec summary may get verdict appended)."""
        narrator = _narrator_dict(executive_summary="Custom GO summary here.")
        merged = merge_scorer_narrator(_scorer_dict(), narrator)
        assert "Custom" in merged["executive_summary"]
        assert "GO" in merged["executive_summary"]
        assert merged["lean_canvas"]["revenue_model"] == narrator["lean_canvas"]["revenue_model"]

    def test_default_confidence(self):
        """Missing confidence_hint defaults to MEDIUM."""
        scorer = _scorer_dict(confidence_hint="")
        merged = merge_scorer_narrator(scorer, _narrator_dict())
        assert merged["confidence"] == "MEDIUM"

    def test_confidence_from_hint(self):
        """confidence_hint propagates to confidence field."""
        scorer = _scorer_dict(confidence_hint="HIGH")
        merged = merge_scorer_narrator(scorer, _narrator_dict())
        assert merged["confidence"] == "HIGH"

    def test_counter_signals_default_empty(self):
        """Missing counter_signals defaults to empty list."""
        scorer = _scorer_dict()
        del scorer["counter_signals"]
        merged = merge_scorer_narrator(scorer, _narrator_dict())
        assert merged["go_no_go_assessment"]["counter_signals"] == []

    def test_exec_summary_verdict_corrected(self):
        """Narrator says NO-GO but scorer says PIVOT → exec summary patched."""
        narrator = _narrator_dict(
            executive_summary="The concept has a NO-GO verdict with LOW confidence."
        )
        scorer = _scorer_dict(recommendation="PIVOT")
        merged = merge_scorer_narrator(scorer, narrator)
        assert "PIVOT" in merged["executive_summary"]
        assert "NO-GO" not in merged["executive_summary"]

    def test_exec_summary_correct_verdict_preserved(self):
        """Narrator already correct → no change."""
        narrator = _narrator_dict(executive_summary="PIVOT recommendation with MEDIUM confidence.")
        scorer = _scorer_dict(recommendation="PIVOT")
        merged = merge_scorer_narrator(scorer, narrator)
        assert merged["executive_summary"] == "PIVOT recommendation with MEDIUM confidence."


# =============================================================================
# _fix_exec_summary_verdict unit tests
# =============================================================================


class TestFixExecSummaryVerdict:
    def test_correct_verdict_unchanged(self):
        text = "The concept receives a GO recommendation."
        assert _fix_exec_summary_verdict(text, "GO") == text

    def test_nogo_replaced_with_pivot(self):
        result = _fix_exec_summary_verdict(
            "The scorer's verdict is NO-GO with MEDIUM confidence.", "PIVOT"
        )
        assert "PIVOT" in result
        assert "NO-GO" not in result

    def test_conditional_go_maps_to_pivot(self):
        """CONDITIONAL GO in text matches PIVOT recommendation — no change."""
        text = "Verdict: CONDITIONAL GO. Evidence quality: MEDIUM."
        result = _fix_exec_summary_verdict(text, "PIVOT")
        assert result == text  # CONDITIONAL GO normalises to PIVOT, which matches

    def test_no_verdict_appends(self):
        result = _fix_exec_summary_verdict("A great startup concept.", "GO")
        assert result.endswith("GO recommendation.")

    def test_case_insensitive(self):
        result = _fix_exec_summary_verdict("The verdict is no-go.", "PIVOT")
        assert "PIVOT" in result

    def test_nogo_variant_replaced(self):
        """'NOGO' (no hyphen) is also caught."""
        result = _fix_exec_summary_verdict("Assessment: NOGO. Bad outlook.", "GO")
        assert "GO" in result


# =============================================================================
# Orchestrator tests (mocked agent calls)
# =============================================================================


def _mock_state(**overrides):
    """Build a mock Burr State with .get() support."""
    defaults = {
        "system_goal": "A scheduling SaaS for remote teams",
        "idea_analysis": "## Idea Analysis\nScheduling tool...",
        "market_context": "## Market Context\n$4B market...",
        "risk_assessment": (
            "## Risk Assessment\nOverall Risk Level: MEDIUM\nExternal Validation: 5/8"
        ),
        "pivot_strategy": "",
        "session_manager": None,
        "concept_anchor_str": "",
    }
    defaults.update(overrides)
    state = mock.MagicMock()
    state.get = lambda key, default="": defaults.get(key, default)
    return state


class TestRunValidationSummarySequential:
    @mock.patch("haytham.workflow.burr_actions.save_stage_output")
    @mock.patch("haytham.workflow.burr_actions.run_agent")
    def test_happy_path(self, mock_run_agent, mock_save):
        """Both agents succeed → returns valid merged JSON with 'completed'."""
        from haytham.workflow.stages.idea_validation import (
            run_validation_summary_sequential,
        )

        scorer_json = json.dumps(_scorer_dict())
        narrator_json = json.dumps(_narrator_dict())

        mock_run_agent.side_effect = [
            {"output": scorer_json, "status": "completed"},
            {"output": narrator_json, "status": "completed"},
        ]

        output, status = run_validation_summary_sequential(_mock_state())

        assert status == "completed"
        parsed = json.loads(output)
        # Validate it's a valid ValidationSummaryOutput
        model = ValidationSummaryOutput.model_validate(parsed)
        assert model.recommendation == "GO"
        assert model.go_no_go_assessment.composite_score == 3.4
        assert "scheduling" in model.executive_summary.lower()

    @mock.patch("haytham.workflow.burr_actions.save_stage_output")
    @mock.patch("haytham.workflow.burr_actions.run_agent")
    def test_scorer_failure(self, mock_run_agent, mock_save):
        """Scorer fails → returns early with 'failed'."""
        from haytham.workflow.stages.idea_validation import (
            run_validation_summary_sequential,
        )

        mock_run_agent.return_value = {
            "output": "Error: token limit exceeded",
            "status": "failed",
            "error": "token_limit",
        }

        output, status = run_validation_summary_sequential(_mock_state())

        assert status == "failed"
        # run_agent only called once (no narrator call)
        assert mock_run_agent.call_count == 1

    @mock.patch("haytham.workflow.burr_actions.save_stage_output")
    @mock.patch("haytham.workflow.burr_actions.run_agent")
    def test_narrator_failure(self, mock_run_agent, mock_save):
        """Narrator fails → returns scorer output with 'partial'."""
        from haytham.workflow.stages.idea_validation import (
            run_validation_summary_sequential,
        )

        scorer_json = json.dumps(_scorer_dict())
        mock_run_agent.side_effect = [
            {"output": scorer_json, "status": "completed"},
            {"output": "Error: narrator failed", "status": "failed", "error": "unknown"},
        ]

        output, status = run_validation_summary_sequential(_mock_state())

        assert status == "partial"
        # Output should be the scorer output (fallback)
        assert output == scorer_json

    @mock.patch("haytham.workflow.burr_actions.save_stage_output")
    @mock.patch("haytham.workflow.burr_actions.run_agent")
    def test_scorer_invalid_json(self, mock_run_agent, mock_save):
        """Scorer returns non-JSON → returns 'failed'."""
        from haytham.workflow.stages.idea_validation import (
            run_validation_summary_sequential,
        )

        mock_run_agent.return_value = {
            "output": "This is not JSON",
            "status": "completed",
        }

        output, status = run_validation_summary_sequential(_mock_state())

        assert status == "failed"

    @mock.patch("haytham.workflow.burr_actions.save_stage_output")
    @mock.patch("haytham.workflow.burr_actions.run_agent")
    def test_scorer_missing_fields(self, mock_run_agent, mock_save):
        """Scorer output missing critical fields → returns 'failed'."""
        from haytham.workflow.stages.idea_validation import (
            run_validation_summary_sequential,
        )

        incomplete = {"knockout_criteria": [], "scorecard": []}
        mock_run_agent.return_value = {
            "output": json.dumps(incomplete),
            "status": "completed",
        }

        output, status = run_validation_summary_sequential(_mock_state())

        assert status == "failed"
