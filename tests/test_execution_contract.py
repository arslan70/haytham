"""Tests for the Execution Contract schema, Gherkin parser, and assembler.

Follows project test patterns: module-level _SAMPLE_* constants, _make_*()
helpers, mock.MagicMock for session_manager, tmp_path for filesystem tests.
"""

import json
from pathlib import Path
from unittest import mock

import pytest

from haytham.workflow.contracts.assembler import (
    _extract_summary,
    _parse_traits_from_markdown,
    _split_implements,
    assemble_execution_contract,
)
from haytham.workflow.contracts.execution_contract import (
    AcceptanceCriterion,
    ContractMetadata,
    ContractStory,
    ExecutionContract,
)
from haytham.workflow.contracts.gherkin_parser import parse_acceptance_criteria

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_SAMPLE_STORY_DICT = {
    "id": "STORY-001",
    "title": "User registration",
    "layer": 0,
    "implements": ["CAP-F-001", "CAP-NF-002", "DEC-003"],
    "depends_on": [],
    "content": (
        "## User Registration\n"
        "- [ ] Given a new user, When they submit the form, Then an account is created\n"
    ),
}

_SAMPLE_STORY_WITH_FENCED_GHERKIN = {
    "id": "STORY-002",
    "title": "User login",
    "layer": 0,
    "implements": ["CAP-F-002"],
    "depends_on": ["STORY-001"],
    "content": (
        "## User Login\n"
        "```gherkin\n"
        "Scenario: Successful login\n"
        "Given a registered user\n"
        "When they enter valid credentials\n"
        "Then they see the dashboard\n"
        "```\n"
    ),
}

_SAMPLE_STORY_WITH_UNFENCED_GHERKIN = {
    "id": "STORY-003",
    "title": "Password reset",
    "layer": 1,
    "implements": ["CAP-F-003", "DEC-005"],
    "depends_on": ["STORY-001"],
    "content": (
        "## Password Reset\n"
        "**Scenario:** Reset via email\n"
        "Given a user who forgot their password\n"
        "When they request a reset link\n"
        "Then an email is sent with a reset token\n"
    ),
}

_SAMPLE_STORY_NO_AC = {
    "id": "STORY-004",
    "title": "Database setup",
    "layer": 0,
    "implements": ["DEC-001"],
    "depends_on": [],
    "content": "## Database Setup\nConfigure PostgreSQL with migrations.",
}

_SAMPLE_TRAITS_MARKDOWN = (
    "**Interface:** Web\n"
    "**Auth:** OAuth2\n"
    "**Deployment:** [Container, Serverless]\n"
    "**Data_layer:** PostgreSQL\n"
    "**Realtime:** None\n"
    "**Communication:** Email\n"
    "**Payments:** None\n"
    "**Scheduling:** None\n"
)


def _make_session_manager(
    traits_markdown=_SAMPLE_TRAITS_MARKDOWN,
    system_goal="A gym leaderboard app",
):
    sm = mock.MagicMock()
    sm.session_dir = Path("/tmp/fake-session")
    sm.load_stage_output.return_value = traits_markdown
    sm.get_system_goal.return_value = system_goal
    return sm


# ===========================================================================
# Gherkin Parser
# ===========================================================================


class TestGherkinParser:
    def test_checkbox_format(self):
        content = "- [ ] Given a new user, When they register, Then an account is created"
        result = parse_acceptance_criteria(content)
        assert len(result) == 1
        assert result[0].given == "a new user"
        assert result[0].when == "they register"
        assert result[0].then == "an account is created"

    def test_checked_checkbox(self):
        content = "- [x] Given a user, When they log in, Then they see home"
        result = parse_acceptance_criteria(content)
        assert len(result) == 1
        assert result[0].given == "a user"

    def test_fenced_gherkin(self):
        content = (
            "```gherkin\n"
            "Scenario: User logs in\n"
            "Given a registered user\n"
            "When they enter credentials\n"
            "Then they see the dashboard\n"
            "```\n"
        )
        result = parse_acceptance_criteria(content)
        assert len(result) == 1
        assert result[0].scenario == "User logs in"
        assert result[0].given == "a registered user"
        assert result[0].when == "they enter credentials"
        assert result[0].then == "they see the dashboard"

    def test_unfenced_gherkin(self):
        content = (
            "**Scenario:** Login flow\n"
            "Given a user\n"
            "When they click login\n"
            "Then access is granted\n"
        )
        result = parse_acceptance_criteria(content)
        assert len(result) == 1
        assert result[0].scenario == "Login flow"
        assert result[0].given == "a user"
        assert result[0].when == "they click login"
        assert result[0].then == "access is granted"

    def test_mixed_formats(self):
        content = (
            "- [ ] Given a user, When they sign up, Then they get a welcome email\n"
            "\n"
            "```gherkin\n"
            "Scenario: Duplicate email\n"
            "Given an existing email\n"
            "When they try to register\n"
            "Then an error is shown\n"
            "```\n"
        )
        result = parse_acceptance_criteria(content)
        assert len(result) == 2
        assert result[0].id == "AC-001"
        assert result[1].id == "AC-002"
        assert result[1].scenario == "Duplicate email"

    def test_non_gherkin_lines_ignored(self):
        content = "Must support 1000 concurrent users\nSome other requirement"
        result = parse_acceptance_criteria(content)
        assert len(result) == 0

    def test_sequential_ids(self):
        content = (
            "- [ ] Given A, When B, Then C\n"
            "- [ ] Given D, When E, Then F\n"
            "- [ ] Given G, When H, Then I\n"
        )
        result = parse_acceptance_criteria(content)
        assert [ac.id for ac in result] == ["AC-001", "AC-002", "AC-003"]

    def test_empty_content(self):
        assert parse_acceptance_criteria("") == []
        assert parse_acceptance_criteria("   ") == []

    def test_given_without_scenario_creates_scenario(self):
        content = "Given a user\nWhen they act\nThen something happens"
        result = parse_acceptance_criteria(content)
        assert len(result) == 1
        assert result[0].scenario == "Given a user"

    def test_plain_fence_without_gherkin_label(self):
        content = "```\nScenario: Test\nGiven X\nWhen Y\nThen Z\n```"
        result = parse_acceptance_criteria(content)
        assert len(result) == 1
        assert result[0].scenario == "Test"


# ===========================================================================
# Contract Models
# ===========================================================================


class TestContractModels:
    def test_json_roundtrip(self):
        contract = ExecutionContract(
            metadata=ContractMetadata(
                generated_at="2026-01-01T00:00:00Z",
                idea_summary="Test idea",
                appetite="Small",
            ),
            system_traits={"interface": "Web", "deployment": ["Container", "Serverless"]},
            stories=[
                ContractStory(
                    id="STORY-001",
                    title="Test story",
                    layer=0,
                    summary="Test summary",
                    implements=["CAP-F-001"],
                    uses=["DEC-001"],
                    depends_on=[],
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id="AC-001",
                            scenario="Test scenario",
                            given="a user",
                            when="they act",
                            then="result",
                        )
                    ],
                    content="## Test\nSome content",
                )
            ],
        )
        json_str = contract.model_dump_json()
        restored = ExecutionContract.model_validate_json(json_str)
        assert restored.schema_version == "1.0"
        assert restored.stories[0].id == "STORY-001"
        assert restored.stories[0].acceptance_criteria[0].given == "a user"
        assert restored.system_traits["deployment"] == ["Container", "Serverless"]

    def test_schema_version_default(self):
        contract = ExecutionContract(
            metadata=ContractMetadata(
                generated_at="2026-01-01T00:00:00Z",
                idea_summary="Test",
            ),
        )
        assert contract.schema_version == "1.0"

    def test_system_traits_accepts_lists(self):
        contract = ExecutionContract(
            metadata=ContractMetadata(
                generated_at="2026-01-01T00:00:00Z",
                idea_summary="Test",
            ),
            system_traits={
                "interface": "Web",
                "deployment": ["Container", "Serverless"],
            },
        )
        assert contract.system_traits["deployment"] == ["Container", "Serverless"]
        assert contract.system_traits["interface"] == "Web"

    def test_to_json_produces_valid_json(self):
        contract = ExecutionContract(
            metadata=ContractMetadata(
                generated_at="2026-01-01T00:00:00Z",
                idea_summary="Test",
            ),
        )
        parsed = json.loads(contract.to_json())
        assert parsed["schema_version"] == "1.0"


# ===========================================================================
# Assembler helpers
# ===========================================================================


class TestCapDecSplit:
    def test_split_mixed_refs(self):
        caps, decs = _split_implements(["CAP-F-001", "CAP-NF-002", "DEC-003"])
        assert caps == ["CAP-F-001", "CAP-NF-002"]
        assert decs == ["DEC-003"]

    def test_cap_nf_stays_in_implements(self):
        caps, decs = _split_implements(["CAP-NF-001"])
        assert caps == ["CAP-NF-001"]
        assert decs == []

    def test_empty_list(self):
        caps, decs = _split_implements([])
        assert caps == []
        assert decs == []

    def test_unknown_prefix_excluded_from_both(self):
        caps, decs = _split_implements(["ENT-001", "CAP-F-001"])
        assert caps == ["CAP-F-001"]
        assert decs == []


class TestSummaryExtraction:
    def test_heading_stripped(self):
        assert _extract_summary("## User Registration\nContent", "fallback") == "User Registration"

    def test_multiple_hashes(self):
        assert _extract_summary("### Deep Heading\nContent", "fallback") == "Deep Heading"

    def test_no_heading(self):
        assert _extract_summary("Plain first line\nSecond", "fallback") == "Plain first line"

    def test_empty_content_fallback(self):
        assert _extract_summary("", "My Title") == "My Title"

    def test_whitespace_only_fallback(self):
        assert _extract_summary("   \n  \n", "My Title") == "My Title"


class TestTraitsParsing:
    def test_basic_traits(self):
        md = "**Interface:** Web\n**Auth:** OAuth2"
        traits = _parse_traits_from_markdown(md)
        assert traits["interface"] == "Web"
        assert traits["auth"] == "OAuth2"

    def test_multi_select_bracket(self):
        md = "**Deployment:** [Container, Serverless]"
        traits = _parse_traits_from_markdown(md)
        assert traits["deployment"] == ["Container", "Serverless"]

    def test_ambiguous_marker_stripped(self):
        md = "**Interface:** Web (ambiguous)"
        traits = _parse_traits_from_markdown(md)
        assert traits["interface"] == "Web"

    def test_non_trait_lines_ignored(self):
        md = "Some random text\n**Interface:** Web\n- bullet point"
        traits = _parse_traits_from_markdown(md)
        assert traits == {"interface": "Web"}

    def test_empty_value_skipped(self):
        md = "**Interface:**"
        traits = _parse_traits_from_markdown(md)
        assert "interface" not in traits


# ===========================================================================
# Full assembly
# ===========================================================================


class TestContractAssembler:
    def test_full_assembly(self):
        sm = _make_session_manager()
        stories = [_SAMPLE_STORY_DICT, _SAMPLE_STORY_WITH_FENCED_GHERKIN, _SAMPLE_STORY_NO_AC]
        contract = assemble_execution_contract(stories, sm, "A gym leaderboard")

        assert contract.schema_version == "1.0"
        assert contract.metadata.idea_summary == "A gym leaderboard"
        assert len(contract.stories) == 3
        assert contract.system_traits["interface"] == "Web"
        assert contract.system_traits["deployment"] == ["Container", "Serverless"]

    def test_cap_dec_split_in_assembly(self):
        sm = _make_session_manager()
        contract = assemble_execution_contract([_SAMPLE_STORY_DICT], sm, "test")

        story = contract.stories[0]
        assert story.implements == ["CAP-F-001", "CAP-NF-002"]
        assert story.uses == ["DEC-003"]

    def test_acceptance_criteria_parsed(self):
        sm = _make_session_manager()
        contract = assemble_execution_contract([_SAMPLE_STORY_WITH_FENCED_GHERKIN], sm, "test")

        story = contract.stories[0]
        assert len(story.acceptance_criteria) == 1
        assert story.acceptance_criteria[0].scenario == "Successful login"

    def test_no_traits_output(self):
        sm = _make_session_manager(traits_markdown=None)
        sm.load_stage_output.return_value = None
        contract = assemble_execution_contract([_SAMPLE_STORY_DICT], sm, "test")
        assert contract.system_traits == {}

    def test_summary_from_content(self):
        sm = _make_session_manager()
        contract = assemble_execution_contract([_SAMPLE_STORY_DICT], sm, "test")
        assert contract.stories[0].summary == "User Registration"

    def test_summary_fallback_to_title(self):
        sm = _make_session_manager()
        story = {**_SAMPLE_STORY_NO_AC, "content": ""}
        contract = assemble_execution_contract([story], sm, "test")
        assert contract.stories[0].summary == "Database setup"


# ===========================================================================
# Pipeline integration (filesystem)
# ===========================================================================


class TestSaveExecutionContract:
    def test_saves_contract_json(self, tmp_path):
        from haytham.workflow.stages.story_pipeline import save_execution_contract

        # Set up session directory with stories.json
        story_gen_dir = tmp_path / "session" / "story-generation"
        story_gen_dir.mkdir(parents=True)
        stories_json = [_SAMPLE_STORY_DICT, _SAMPLE_STORY_WITH_FENCED_GHERKIN]
        (story_gen_dir / "stories.json").write_text(json.dumps(stories_json))

        sm = mock.MagicMock()
        sm.session_dir = tmp_path / "session"
        sm.load_stage_output.return_value = _SAMPLE_TRAITS_MARKDOWN
        sm.get_system_goal.return_value = "A gym leaderboard app"

        save_execution_contract(sm, "some output text")

        contract_path = story_gen_dir / "execution_contract.json"
        assert contract_path.exists()
        data = json.loads(contract_path.read_text())
        assert data["schema_version"] == "1.0"
        assert len(data["stories"]) == 2

    def test_contract_matches_stories_count(self, tmp_path):
        from haytham.workflow.stages.story_pipeline import save_execution_contract

        story_gen_dir = tmp_path / "session" / "story-generation"
        story_gen_dir.mkdir(parents=True)
        stories = [_SAMPLE_STORY_DICT, _SAMPLE_STORY_WITH_FENCED_GHERKIN, _SAMPLE_STORY_NO_AC]
        (story_gen_dir / "stories.json").write_text(json.dumps(stories))

        sm = mock.MagicMock()
        sm.session_dir = tmp_path / "session"
        sm.load_stage_output.return_value = _SAMPLE_TRAITS_MARKDOWN
        sm.get_system_goal.return_value = "test"

        save_execution_contract(sm, "output")

        data = json.loads((story_gen_dir / "execution_contract.json").read_text())
        assert len(data["stories"]) == len(stories)

    def test_missing_stories_json_no_crash(self, tmp_path):
        from haytham.workflow.stages.story_pipeline import save_execution_contract

        # No stories.json on disk
        story_gen_dir = tmp_path / "session" / "story-generation"
        story_gen_dir.mkdir(parents=True)

        sm = mock.MagicMock()
        sm.session_dir = tmp_path / "session"

        # Should return without error
        save_execution_contract(sm, "output")
        assert not (story_gen_dir / "execution_contract.json").exists()


# ===========================================================================
# JSON Schema validation
# ===========================================================================


_SCHEMA_FILE = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "architecture"
    / "execution-contract-schema.json"
)


class TestSchemaValidation:
    def test_checked_in_schema_matches_model(self):
        """Guard against stale schema: the checked-in JSON must match the model."""
        assert _SCHEMA_FILE.exists(), f"Schema file not found: {_SCHEMA_FILE}"
        on_disk = json.loads(_SCHEMA_FILE.read_text())
        from_model = ExecutionContract.model_json_schema()
        assert on_disk == from_model, (
            "docs/architecture/execution-contract-schema.json is stale. "
            "Regenerate with: ExecutionContract.model_json_schema()"
        )

    def test_contract_validates_against_json_schema(self):
        jsonschema = pytest.importorskip("jsonschema")

        schema = ExecutionContract.model_json_schema()
        contract = ExecutionContract(
            metadata=ContractMetadata(
                generated_at="2026-01-01T00:00:00Z",
                idea_summary="Test",
                appetite="Small",
            ),
            system_traits={"interface": "Web"},
            stories=[
                ContractStory(
                    id="STORY-001",
                    title="Test",
                    layer=0,
                    summary="Test",
                    implements=["CAP-F-001"],
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id="AC-001", scenario="Test", given="X", when="Y", then="Z"
                        )
                    ],
                )
            ],
        )
        instance = json.loads(contract.model_dump_json())
        jsonschema.validate(instance, schema)
