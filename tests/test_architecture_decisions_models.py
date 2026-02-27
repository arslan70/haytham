"""Tests for ArchitectureDecisionsOutput Pydantic model."""

import pytest
from pydantic import ValidationError

from haytham.agents.worker_architecture_decisions.architecture_decisions_models import (
    ArchitectureDecision,
    ArchitectureDecisionsOutput,
)

VALID_DECISION = {
    "id": "DEC-AUTH-001",
    "name": "Authentication Strategy",
    "description": "Use Supabase Auth for user authentication",
    "rationale": "Integrates with existing Supabase database choice",
    "serves_capabilities": ["CAP-F-001", "CAP-NF-002"],
    "implements_recommendation": "Supabase Auth",
    "alternatives_considered": [
        "Auth0 - more expensive at scale",
        "Firebase Auth - vendor lock-in with Google",
    ],
}

VALID_PAYLOAD = {
    "decisions": [VALID_DECISION],
    "coverage_check": {
        "functional_capabilities_covered": ["CAP-F-001"],
        "non_functional_capabilities_covered": ["CAP-NF-002"],
        "uncovered_capabilities": [],
    },
    "summary": "Lean architecture leveraging managed services for fast MVP delivery.",
}


def test_validates_good_data():
    """Construct from a valid dict and assert field values."""
    output = ArchitectureDecisionsOutput.model_validate(VALID_PAYLOAD)

    assert len(output.decisions) == 1
    dec = output.decisions[0]
    assert dec.id == "DEC-AUTH-001"
    assert dec.name == "Authentication Strategy"
    assert dec.serves_capabilities == ["CAP-F-001", "CAP-NF-002"]
    assert dec.implements_recommendation == "Supabase Auth"
    assert len(dec.alternatives_considered) == 2

    assert output.coverage_check.functional_capabilities_covered == ["CAP-F-001"]
    assert output.coverage_check.non_functional_capabilities_covered == ["CAP-NF-002"]
    assert output.coverage_check.uncovered_capabilities == []
    assert output.summary.startswith("Lean architecture")


def test_roundtrip_json():
    """model_dump_json -> model_validate_json roundtrip preserves data."""
    original = ArchitectureDecisionsOutput.model_validate(VALID_PAYLOAD)
    json_str = original.model_dump_json()
    restored = ArchitectureDecisionsOutput.model_validate_json(json_str)

    assert restored == original


def test_to_markdown_contains_decisions():
    """Assert key strings appear in the rendered markdown."""
    output = ArchitectureDecisionsOutput.model_validate(VALID_PAYLOAD)
    md = output.to_markdown()

    assert "# Architecture Decisions" in md
    assert "DEC-AUTH-001" in md
    assert "Authentication Strategy" in md
    assert "Supabase Auth" in md
    assert "CAP-F-001" in md
    assert "Alternatives Considered" in md
    assert "Auth0 - more expensive at scale" in md
    assert "Coverage Summary" in md
    assert "Total decisions:" in md


def test_rejects_missing_decisions():
    """model_validate({}) should raise ValidationError for missing 'decisions'."""
    with pytest.raises(ValidationError):
        ArchitectureDecisionsOutput.model_validate({})


def test_decision_defaults():
    """Minimal decision with required fields only; defaults fill in."""
    minimal = ArchitectureDecision(
        id="DEC-DB-001",
        name="Database",
        description="Use PostgreSQL",
        rationale="Battle-tested",
        serves_capabilities=["CAP-F-001"],
        implements_recommendation="PostgreSQL",
    )
    assert minimal.alternatives_considered == []

    output = ArchitectureDecisionsOutput(decisions=[minimal])
    assert output.summary == ""
    assert output.coverage_check.functional_capabilities_covered == []
    assert output.coverage_check.uncovered_capabilities == []
