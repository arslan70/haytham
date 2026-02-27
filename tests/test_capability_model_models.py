"""Tests for CapabilityModelOutput Pydantic models."""

import json

import pytest
from pydantic import ValidationError

from haytham.agents.worker_capability_model.capability_model_models import (
    CapabilityModelOutput,
)


def _full_valid_dict() -> dict:
    """Return a complete, valid capability model dict."""
    return {
        "summary": {
            "system_name": "FitTracker",
            "system_purpose": "Track workouts and compete on leaderboards",
            "primary_user_segment": "People who go to the gym regularly",
            "input_method": "Manual entry via mobile app",
            "mvp_scope_respected": True,
        },
        "capabilities": {
            "functional": [
                {
                    "id": "CAP-F-001",
                    "name": "Workout Logging",
                    "description": "Users can log completed exercises with sets and reps",
                    "serves_scope_item": "Manual workout logging with exercise + sets + reps",
                    "user_flow": "Flow 1",
                    "acceptance_criteria": [
                        "User can select exercise from list",
                        "User can enter sets and reps",
                    ],
                    "rationale": "Core input mechanism for the gamification loop",
                },
            ],
            "non_functional": [
                {
                    "id": "CAP-NF-001",
                    "name": "Page Load Speed",
                    "description": "App screens load quickly",
                    "category": "performance",
                    "requirement": "Under 2s on 3G",
                    "measurement": "Lighthouse audit",
                    "rationale": "Mobile users expect fast loads",
                },
            ],
        },
        "traceability": {
            "scope_items_covered": [
                "Manual workout logging with exercise + sets + reps",
            ],
            "scope_items_not_covered": [],
            "flows_covered": ["Flow 1"],
        },
        "metadata": {
            "functional_count": 1,
            "non_functional_count": 1,
        },
    }


def test_validates_good_data():
    """Full valid dict round-trips through the model."""
    data = _full_valid_dict()
    model = CapabilityModelOutput.model_validate(data)

    assert model.summary.system_name == "FitTracker"
    assert model.summary.mvp_scope_respected is True
    assert len(model.capabilities.functional) == 1
    assert model.capabilities.functional[0].id == "CAP-F-001"
    assert model.capabilities.functional[0].serves_scope_item == (
        "Manual workout logging with exercise + sets + reps"
    )
    assert len(model.capabilities.non_functional) == 1
    assert model.capabilities.non_functional[0].category == "performance"
    assert model.metadata.functional_count == 1
    assert model.metadata.non_functional_count == 1


def test_roundtrip_json():
    """model_dump_json -> model_validate_json preserves all fields."""
    data = _full_valid_dict()
    model = CapabilityModelOutput.model_validate(data)

    json_str = model.model_dump_json(indent=2)
    restored = CapabilityModelOutput.model_validate_json(json_str)

    assert restored.summary.system_name == model.summary.system_name
    assert len(restored.capabilities.functional) == len(model.capabilities.functional)
    assert restored.capabilities.functional[0].id == model.capabilities.functional[0].id
    assert restored.traceability.flows_covered == model.traceability.flows_covered
    assert restored.metadata.functional_count == model.metadata.functional_count

    # Verify JSON is valid
    parsed = json.loads(json_str)
    assert parsed["summary"]["system_name"] == "FitTracker"


def test_scope_items_covered():
    """Traceability field stores scope items correctly."""
    data = _full_valid_dict()
    data["traceability"]["scope_items_covered"] = ["Item A", "Item B"]
    data["traceability"]["scope_items_not_covered"] = ["Item C - deferred"]

    model = CapabilityModelOutput.model_validate(data)

    assert model.traceability.scope_items_covered == ["Item A", "Item B"]
    assert model.traceability.scope_items_not_covered == ["Item C - deferred"]


def test_rejects_missing_capabilities():
    """Dict without capabilities key raises ValidationError."""
    data = _full_valid_dict()
    del data["capabilities"]

    with pytest.raises(ValidationError):
        CapabilityModelOutput.model_validate(data)


def test_defaults_fill_in():
    """Minimal dict with just capabilities works; defaults fill the rest."""
    minimal = {
        "capabilities": {
            "functional": [
                {
                    "id": "CAP-F-001",
                    "name": "Basic Feature",
                    "description": "Does something",
                    "serves_scope_item": "Some scope item",
                },
            ],
        },
    }
    model = CapabilityModelOutput.model_validate(minimal)

    # summary defaults
    assert model.summary.system_name == ""
    assert model.summary.mvp_scope_respected is True

    # functional capability defaults
    cap = model.capabilities.functional[0]
    assert cap.user_flow == ""
    assert cap.acceptance_criteria == []
    assert cap.rationale == ""

    # non_functional defaults to empty list
    assert model.capabilities.non_functional == []

    # traceability defaults
    assert model.traceability.scope_items_covered == []
    assert model.traceability.flows_covered == []

    # metadata defaults
    assert model.metadata.functional_count == 0
    assert model.metadata.non_functional_count == 0
