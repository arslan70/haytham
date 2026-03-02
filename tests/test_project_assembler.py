"""Tests for haytham.exporters.project_assembler."""

import json
from pathlib import Path

import pytest

from haytham.exporters.project_assembler import assemble_exportable_project

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_session_files(session_dir: Path) -> None:
    """Write minimal but realistic session JSON files for all 4 inputs.

    Creates:
      - story-generation/execution_contract.json  (2 stories)
      - capability-model/output.json              (1 functional + 1 NF cap)
      - architecture-decisions/output.json        (1 decision)
      - build-buy-analysis/output.json            (1 stack recommendation)
    """
    # --- Execution contract ---
    contract = {
        "schema_version": "1.0",
        "metadata": {
            "generated_at": "2026-02-28T12:00:00Z",
            "idea_summary": "Fitness leaderboard app",
            "appetite": "6 weeks",
        },
        "system_traits": {"interface": "web", "auth": "multi_user"},
        "stories": [
            {
                "id": "STORY-001",
                "title": "User Registration",
                "layer": 1,
                "summary": "Allow users to register",
                "implements": ["CAP-F-001"],
                "uses": [],
                "depends_on": [],
                "acceptance_criteria": [],
                "content": "",
            },
            {
                "id": "STORY-002",
                "title": "Setup CI pipeline",
                "layer": 0,
                "summary": "Infrastructure setup",
                "implements": [],
                "uses": [],
                "depends_on": [],
                "acceptance_criteria": [],
                "content": "",
            },
        ],
    }
    story_dir = session_dir / "story-generation"
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "execution_contract.json").write_text(
        json.dumps(contract, indent=2), encoding="utf-8"
    )

    # --- Capability model ---
    cap_model = {
        "summary": {
            "system_name": "FitBoard",
            "system_purpose": "Community fitness leaderboard",
            "primary_user_segment": "Gym-goers",
            "input_method": "web form",
            "mvp_scope_respected": True,
        },
        "capabilities": {
            "functional": [
                {
                    "id": "CAP-F-001",
                    "name": "User Authentication",
                    "description": "Allow users to register and log in",
                    "serves_scope_item": "User Auth",
                    "user_flow": "Flow 1",
                    "acceptance_criteria": ["Users can register", "Users can log in"],
                    "rationale": "Core user management",
                }
            ],
            "non_functional": [
                {
                    "id": "CAP-NF-001",
                    "name": "Page Load Performance",
                    "description": "Pages load within 2 seconds",
                    "category": "performance",
                    "requirement": "Page load < 2s on 3G",
                    "measurement": "Lighthouse score > 80",
                    "rationale": "User retention",
                }
            ],
        },
        "traceability": {
            "scope_items_covered": ["User Auth"],
            "scope_items_not_covered": [],
            "flows_covered": ["Flow 1"],
        },
        "metadata": {"functional_count": 1, "non_functional_count": 1},
    }
    cap_dir = session_dir / "capability-model"
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "output.json").write_text(json.dumps(cap_model, indent=2), encoding="utf-8")

    # --- Architecture decisions ---
    arch = {
        "decisions": [
            {
                "id": "DEC-AUTH-001",
                "name": "Supabase Auth",
                "description": "Use Supabase for authentication",
                "rationale": "Quick setup, generous free tier",
                "serves_capabilities": ["CAP-F-001"],
                "implements_recommendation": "Supabase Auth",
                "alternatives_considered": ["Auth0", "Firebase Auth"],
            }
        ],
        "coverage_check": {
            "functional_capabilities_covered": ["CAP-F-001"],
            "non_functional_capabilities_covered": ["CAP-NF-001"],
            "uncovered_capabilities": [],
        },
        "summary": "Supabase-based architecture",
    }
    arch_dir = session_dir / "architecture-decisions"
    arch_dir.mkdir(parents=True, exist_ok=True)
    (arch_dir / "output.json").write_text(json.dumps(arch, indent=2), encoding="utf-8")

    # --- Build-buy analysis ---
    build_buy = {
        "system_summary": "Fitness leaderboard app needing auth and DB",
        "recommended_stack": [
            {
                "name": "Supabase",
                "category": "Database + Auth",
                "recommendation": "BUY",
                "rationale": "All-in-one for MVP",
                "capabilities_served": ["CAP-F-001"],
                "integration_effort": "2-4 hours",
                "pricing_notes": "Free tier sufficient",
            }
        ],
        "stack_rationale": "Single platform reduces integration complexity",
        "infrastructure_requirements": [],
        "alternatives": [],
        "total_integration_effort": "2-4 hours",
        "estimated_monthly_cost": "$0",
    }
    bb_dir = session_dir / "build-buy-analysis"
    bb_dir.mkdir(parents=True, exist_ok=True)
    (bb_dir / "output.json").write_text(json.dumps(build_buy, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProjectAssembler:
    """Tests for assemble_exportable_project."""

    def test_assembles_from_session_files(self, tmp_path):
        """All fields are populated correctly from session JSON files."""
        session_dir = tmp_path / "session"
        _write_session_files(session_dir)

        project = assemble_exportable_project(session_dir)

        # Metadata from contract
        assert project.project_name == "FitBoard"
        assert project.idea_summary == "Fitness leaderboard app"
        assert project.appetite == "6 weeks"
        assert project.generated_at == "2026-02-28T12:00:00Z"
        assert project.system_traits == {"interface": "web", "auth": "multi_user"}

        # Stories
        assert len(project.stories) == 2
        assert project.stories[0].id == "STORY-001"

        # Capabilities
        assert len(project.capabilities) == 1
        cap = project.capabilities[0]
        assert cap.id == "CAP-F-001"
        assert cap.is_functional is True
        assert cap.serves_scope_item == "User Auth"
        assert cap.acceptance_criteria == ["Users can register", "Users can log in"]

        # Non-functional capabilities
        assert len(project.non_functional_capabilities) == 1
        nf = project.non_functional_capabilities[0]
        assert nf.id == "CAP-NF-001"
        assert nf.is_functional is False
        assert nf.serves_scope_item is None
        assert nf.description == "Pages load within 2 seconds"

        # Decisions
        assert len(project.decisions) == 1
        dec = project.decisions[0]
        assert dec.id == "DEC-AUTH-001"
        assert dec.title == "Supabase Auth"
        assert dec.implements == "Supabase Auth"
        assert dec.serves_capabilities == ["CAP-F-001"]
        assert dec.alternatives_considered == ["Auth0", "Firebase Auth"]

        # Build-buy (raw dict)
        assert project.build_buy is not None
        assert project.build_buy["system_summary"] == "Fitness leaderboard app needing auth and DB"

        # Scope items
        assert len(project.scope_items) == 2  # "User Auth" + "Infrastructure" (orphan)
        auth_scope = project.scope_items[0]
        assert auth_scope.name == "User Auth"
        assert auth_scope.capabilities == ["CAP-F-001"]
        assert "STORY-001" in auth_scope.stories

    def test_scope_item_descriptions_from_capabilities(self, tmp_path):
        """Scope item descriptions are synthesized from linked capability descriptions."""
        session_dir = tmp_path / "session"
        _write_session_files(session_dir)

        project = assemble_exportable_project(session_dir)

        auth_scope = project.scope_items[0]
        assert auth_scope.name == "User Auth"
        assert auth_scope.description == "Allow users to register and log in"

    def test_orphan_stories_in_infrastructure(self, tmp_path):
        """Stories without implements go to a synthetic Infrastructure scope item."""
        session_dir = tmp_path / "session"
        _write_session_files(session_dir)

        project = assemble_exportable_project(session_dir)

        infra_items = [s for s in project.scope_items if s.name == "Infrastructure"]
        assert len(infra_items) == 1
        infra = infra_items[0]
        assert "STORY-002" in infra.stories
        assert infra.capabilities == []

    def test_scope_items_from_traceability(self, tmp_path):
        """Scope items are derived from traceability.scope_items_covered."""
        session_dir = tmp_path / "session"
        _write_session_files(session_dir)

        project = assemble_exportable_project(session_dir)

        # The primary scope item should come from traceability, not from
        # deduplication of serves_scope_item values.
        scope_names = [s.name for s in project.scope_items]
        assert "User Auth" in scope_names

    def test_missing_contract_raises(self, tmp_path):
        """FileNotFoundError raised when execution contract is missing."""
        session_dir = tmp_path / "session"
        session_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="Execution contract not found"):
            assemble_exportable_project(session_dir)

    def test_missing_optional_files_ok(self, tmp_path):
        """Assembles successfully with only the execution contract present."""
        session_dir = tmp_path / "session"

        # Write only the execution contract
        contract = {
            "schema_version": "1.0",
            "metadata": {
                "generated_at": "2026-02-28",
                "idea_summary": "Minimal app",
                "appetite": "",
            },
            "system_traits": {},
            "stories": [
                {
                    "id": "STORY-001",
                    "title": "Bootstrap",
                    "layer": 0,
                    "summary": "Initial setup",
                    "implements": [],
                    "uses": [],
                    "depends_on": [],
                    "acceptance_criteria": [],
                    "content": "",
                }
            ],
        }
        story_dir = session_dir / "story-generation"
        story_dir.mkdir(parents=True, exist_ok=True)
        (story_dir / "execution_contract.json").write_text(
            json.dumps(contract, indent=2), encoding="utf-8"
        )

        project = assemble_exportable_project(session_dir)

        assert project.project_name == ""
        assert project.idea_summary == "Minimal app"
        assert len(project.stories) == 1
        assert project.capabilities == []
        assert project.non_functional_capabilities == []
        assert project.decisions == []
        assert project.build_buy is None
        assert project.scope_items == []

    def test_scope_items_fallback_to_serves_scope_item(self, tmp_path):
        """When traceability.scope_items_covered is empty, derive from serves_scope_item."""
        session_dir = tmp_path / "session"
        _write_session_files(session_dir)

        # Overwrite capability model with empty traceability
        cap_model = {
            "capabilities": {
                "functional": [
                    {
                        "id": "CAP-F-001",
                        "name": "User Auth",
                        "description": "Auth capability",
                        "serves_scope_item": "User Auth",
                        "acceptance_criteria": [],
                    },
                    {
                        "id": "CAP-F-002",
                        "name": "Leaderboard",
                        "description": "Show leaderboard",
                        "serves_scope_item": "Leaderboard Display",
                        "acceptance_criteria": [],
                    },
                ],
                "non_functional": [],
            },
            "traceability": {
                "scope_items_covered": [],
                "scope_items_not_covered": [],
                "flows_covered": [],
            },
        }
        cap_path = session_dir / "capability-model" / "output.json"
        cap_path.write_text(json.dumps(cap_model, indent=2), encoding="utf-8")

        project = assemble_exportable_project(session_dir)

        scope_names = [s.name for s in project.scope_items]
        assert "User Auth" in scope_names
        assert "Leaderboard Display" in scope_names

    def test_corrupted_optional_json_treated_as_missing(self, tmp_path):
        """Malformed JSON in optional files is treated as missing (graceful degradation)."""
        session_dir = tmp_path / "session"
        _write_session_files(session_dir)

        # Corrupt the capability model JSON
        cap_path = session_dir / "capability-model" / "output.json"
        cap_path.write_text("{this is not valid json", encoding="utf-8")

        project = assemble_exportable_project(session_dir)

        # Should still assemble, just without capabilities
        assert project.capabilities == []
        assert project.non_functional_capabilities == []
        assert project.scope_items == []
        # Other fields from the valid contract should be intact
        assert project.idea_summary == "Fitness leaderboard app"
        assert len(project.stories) == 2

    def test_nf_capability_uses_requirement_as_description_fallback(self, tmp_path):
        """Non-functional capability uses 'requirement' field when 'description' is empty."""
        session_dir = tmp_path / "session"
        _write_session_files(session_dir)

        # Overwrite capability model with NF cap that has requirement but no description
        cap_model = {
            "capabilities": {
                "functional": [],
                "non_functional": [
                    {
                        "id": "CAP-NF-010",
                        "name": "Uptime",
                        "category": "reliability",
                        "requirement": "99.9% uptime SLA",
                        "measurement": "Monitoring checks",
                    }
                ],
            },
            "traceability": {},
        }
        cap_path = session_dir / "capability-model" / "output.json"
        cap_path.write_text(json.dumps(cap_model, indent=2), encoding="utf-8")

        project = assemble_exportable_project(session_dir)

        nf = project.non_functional_capabilities[0]
        assert nf.description == "99.9% uptime SLA"


# ---------------------------------------------------------------------------
# Concept anchor and recommendation loading (scaffold export support)
# ---------------------------------------------------------------------------


def _write_minimal_session(session_dir: Path) -> None:
    """Write only the execution contract (minimum required for assembly)."""
    contract = {
        "metadata": {
            "idea_summary": "A gym leaderboard app",
            "appetite": "Small Batch",
            "generated_at": "2026-03-01T00:00:00Z",
        },
        "system_traits": {"interface": "web"},
        "stories": [],
    }
    story_dir = session_dir / "story-generation"
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "execution_contract.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )


class TestConceptAnchorLoading:
    def test_concept_anchor_fields_populated(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        anchor = {
            "anchor": {
                "intent": {
                    "goal": "Build a gym app",
                    "explicit_constraints": ["invite-only", "anonymous"],
                    "non_goals": ["not a social media platform", "not public"],
                },
                "identity": [
                    {
                        "feature": "anonymous leaderboard",
                        "why_distinctive": "LLMs tend to add profiles",
                    }
                ],
            }
        }
        (session_dir / "concept_anchor.json").write_text(
            json.dumps(anchor), encoding="utf-8"
        )

        project = assemble_exportable_project(session_dir)
        assert project.explicit_constraints == ["invite-only", "anonymous"]
        assert project.non_goals == ["not a social media platform", "not public"]
        assert "anonymous leaderboard" in project.identity_risks[0]

    def test_missing_concept_anchor_leaves_defaults(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        project = assemble_exportable_project(session_dir)
        assert project.explicit_constraints == []
        assert project.non_goals == []
        assert project.identity_risks == []


class TestRecommendationLoading:
    def test_idea_one_liner_populated(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        rec = {
            "recommendation": "GO",
            "executive_summary": {
                "idea_in_one_line": "A gym leaderboard for CrossFit athletes",
                "strongest_point": "Clear market need",
                "recommendation_summary": "Build it",
                "recommendation_reasoning": "Strong concept",
                "competitive_snapshot": "No direct competitors",
                "closing_remark": "Interview 20 users",
            },
        }
        (session_dir / "recommendation.json").write_text(
            json.dumps(rec), encoding="utf-8"
        )

        project = assemble_exportable_project(session_dir)
        assert project.idea_one_liner == "A gym leaderboard for CrossFit athletes"

    def test_missing_recommendation_leaves_default(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        project = assemble_exportable_project(session_dir)
        assert project.idea_one_liner == ""
