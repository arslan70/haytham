"""Unit tests for stack selection components.

Tests the Session 3 deliverables:
- Stack templates with all required fields
- Platform signal detection from MVP spec
- Stack proposal agent (heuristic only, no LLM)
- Human gates for presenting choices
- StateUpdater.set_stack for recording choices

Reference: ADR-001b: Platform & Stack Proposal

Note: This file is named stack_selection_tests.py to avoid gitignore pattern test_*.py
Run with: pytest tests/stack_selection_tests.py -v
"""

# Import human_gates directly to avoid triggering workflow __init__
# which imports burr (not needed for these tests)
import importlib.util
import tempfile
from pathlib import Path

import pytest
import yaml

from haytham.project.project_state import PipelineStateManager
from haytham.project.stack_templates import (
    PLATFORM_SIGNALS,
    STACK_TEMPLATES,
    detect_platform_signals,
    get_default_template_for_platform,
    get_stack_template,
    get_templates_for_platform,
    list_all_templates,
    recommend_platform,
)
from haytham.project.state_models import PipelineState
from haytham.project.state_updater import StateUpdater

human_gates_path = Path(__file__).parent.parent / "haytham" / "workflow" / "human_gates.py"
spec = importlib.util.spec_from_file_location("human_gates", human_gates_path)
human_gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(human_gates)

format_stack_for_display = human_gates.format_stack_for_display
get_platform_explanation = human_gates.get_platform_explanation
parse_stack_choice = human_gates.parse_stack_choice
present_stack_choices = human_gates.present_stack_choices


# ========== Fixtures ==========


@pytest.fixture
def notes_app_mvp_spec():
    """Load the Notes App MVP spec fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "notes_app_mvp_spec.md"
    with open(fixture_path) as f:
        return f.read()


@pytest.fixture
def cli_app_mvp_spec():
    """MVP spec text with CLI signals."""
    return """
# File Processor CLI

## Core Value Statement
A command-line tool for batch processing files from terminal.

## P0 Features

### Feature: Process Files
**User Story:** As a developer, I want to run a command to process files.

**Acceptance Criteria:**
- Given I have a directory, when I run the process command, files are transformed
- Output is written to stdout or a file
- Script can be run in batch mode

### Feature: Configure Pipeline
**User Story:** As a developer, I want to configure the processing pipeline.

**Acceptance Criteria:**
- Given I have a config file, when I run the tool, it uses my settings
- Can be integrated into automation scripts
- Supports scheduled execution via cron
"""


@pytest.fixture
def api_mvp_spec():
    """MVP spec text with API signals."""
    return """
# Data Integration API

## Core Value Statement
A headless API service for third-party integrations.

## P0 Features

### Feature: REST Endpoints
**User Story:** As an integrator, I want to call API endpoints.

**Acceptance Criteria:**
- Given valid credentials, when I call the endpoint, I get data
- Webhooks notify external services of changes
- No frontend needed - other applications consume this API
"""


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory with project.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        project_file = session_dir / "project.yaml"
        data = {
            "system_goal": "Test App",
            "status": "in_progress",
        }
        with open(project_file, "w") as f:
            yaml.dump(data, f)
        yield session_dir


@pytest.fixture
def empty_pipeline_state():
    """Empty pipeline state for testing."""
    return PipelineState()


# ========== Stack Templates Tests ==========


class TestStackTemplates:
    """Test stack template definitions."""

    def test_all_templates_have_required_fields(self):
        """All templates have platform and backend at minimum."""
        for tid, stack in STACK_TEMPLATES.items():
            assert stack.platform, f"Template {tid} missing platform"
            # Backend should exist for all templates
            assert stack.backend is not None, f"Template {tid} missing backend"
            assert stack.backend.language, f"Template {tid} missing backend language"
            assert stack.backend.framework, f"Template {tid} missing backend framework"

    def test_web_templates_have_frontend(self):
        """Web application templates should have frontend (except HTMX)."""
        web_templates = get_templates_for_platform("web_application")
        for tid, stack in web_templates.items():
            if "htmx" not in tid:
                assert stack.frontend is not None, f"Web template {tid} missing frontend"
                assert stack.frontend.language, f"Template {tid} missing frontend language"

    def test_cli_templates_have_no_frontend(self):
        """CLI templates should not have frontend."""
        cli_templates = get_templates_for_platform("cli")
        for tid, stack in cli_templates.items():
            assert stack.frontend is None, f"CLI template {tid} should not have frontend"

    def test_get_stack_template(self):
        """Can get template by ID."""
        stack = get_stack_template("web-python-react")
        assert stack is not None
        assert stack.platform == "web_application"
        assert stack.backend.language == "python"

    def test_get_stack_template_invalid(self):
        """Returns None for invalid template ID."""
        assert get_stack_template("invalid-template") is None

    def test_get_default_template_for_platform(self):
        """Default templates exist for all platforms."""
        assert get_default_template_for_platform("web_application") == "web-python-react"
        assert get_default_template_for_platform("cli") == "cli-python"
        assert get_default_template_for_platform("api") == "api-python"

    def test_list_all_templates(self):
        """List all templates returns summary info."""
        templates = list_all_templates()
        assert len(templates) >= 6  # At least our defined templates
        for t in templates:
            assert "id" in t
            assert "platform" in t


# ========== Platform Signal Detection Tests ==========


class TestPlatformSignalDetection:
    """Test platform signal detection from MVP specs."""

    def test_notes_app_detected_as_web(self, notes_app_mvp_spec):
        """Notes App should be detected as web application."""
        scores = detect_platform_signals(notes_app_mvp_spec)
        assert scores["web_application"] > scores["cli"]
        assert scores["web_application"] > scores["api"]

    def test_cli_app_detected_as_cli(self, cli_app_mvp_spec):
        """CLI spec should be detected as CLI."""
        scores = detect_platform_signals(cli_app_mvp_spec)
        assert scores["cli"] > 0.1  # Has some CLI signals

    def test_api_app_detected_as_api(self, api_mvp_spec):
        """API spec should be detected as API."""
        scores = detect_platform_signals(api_mvp_spec)
        assert scores["api"] > 0.1  # Has some API signals

    def test_recommend_platform_notes_app(self, notes_app_mvp_spec):
        """Notes App recommends web application."""
        platform, scores = recommend_platform(notes_app_mvp_spec)
        assert platform == "web_application"

    def test_recommend_platform_empty_defaults_to_web(self):
        """Empty spec defaults to web application."""
        platform, _ = recommend_platform("")
        assert platform == "web_application"

    def test_platform_signals_has_all_platforms(self):
        """PLATFORM_SIGNALS covers all platform types."""
        assert "web_application" in PLATFORM_SIGNALS
        assert "cli" in PLATFORM_SIGNALS
        assert "api" in PLATFORM_SIGNALS


# ========== Human Gates Tests ==========


class TestHumanGates:
    """Test human gate presentation and parsing."""

    def test_format_stack_for_display(self):
        """Format stack creates user-friendly display."""
        choice = format_stack_for_display("web-python-react")
        assert choice.template_id == "web-python-react"
        assert choice.platform == "web_application"
        assert "Python" in choice.backend_summary
        assert "Fastapi" in choice.backend_summary
        assert "Typescript" in choice.frontend_summary or "React" in choice.frontend_summary

    def test_format_stack_invalid_template(self):
        """Format handles invalid template gracefully."""
        choice = format_stack_for_display("invalid-template")
        assert choice.template_id == "invalid-template"
        assert choice.platform == "unknown"

    def test_get_platform_explanation(self):
        """Platform explanations exist and are meaningful."""
        web_exp = get_platform_explanation("web_application")
        assert "browser" in web_exp.lower()
        assert "device" in web_exp.lower()

        cli_exp = get_platform_explanation("cli")
        assert "terminal" in cli_exp.lower() or "command" in cli_exp.lower()

    def test_present_stack_choices(self):
        """Present stack choices creates proper presentation."""
        presentation = present_stack_choices(
            recommended_platform="web_application",
            recommended_stack="web-python-react",
            rationale="Best for CRUD apps",
        )

        assert presentation.recommended.template_id == "web-python-react"
        assert presentation.recommended.is_recommended is True
        assert len(presentation.alternatives) >= 1  # Other web stacks
        assert "Platform Decision" in presentation.formatted_text
        assert "Recommended" in presentation.formatted_text

    def test_parse_stack_choice_letter(self):
        """Parse handles letter choices."""
        alternatives = ["web-python-htmx", "web-node-react"]

        # A = recommended
        assert parse_stack_choice("A", "web-python-react", alternatives) == "web-python-react"
        assert parse_stack_choice("a", "web-python-react", alternatives) == "web-python-react"

        # B = first alternative
        assert parse_stack_choice("B", "web-python-react", alternatives) == "web-python-htmx"

        # C = second alternative
        assert parse_stack_choice("C", "web-python-react", alternatives) == "web-node-react"

    def test_parse_stack_choice_template_id(self):
        """Parse handles direct template IDs."""
        alternatives = ["web-python-htmx"]

        result = parse_stack_choice("web-python-htmx", "web-python-react", alternatives)
        assert result == "web-python-htmx"

    def test_parse_stack_choice_invalid(self):
        """Parse returns None for invalid input."""
        result = parse_stack_choice("invalid", "web-python-react", [])
        assert result is None

        result = parse_stack_choice("Z", "web-python-react", [])
        assert result is None


# ========== StateUpdater Stack Tests ==========


class TestStateUpdaterStack:
    """Test StateUpdater stack operations."""

    def test_set_stack_valid_template(self, empty_pipeline_state):
        """set_stack sets stack from valid template."""
        saves = []
        updater = StateUpdater(empty_pipeline_state, lambda s: saves.append(s))

        result = updater.set_stack("web-python-react")

        assert result is True
        assert empty_pipeline_state.stack is not None
        assert empty_pipeline_state.stack.platform == "web_application"
        assert empty_pipeline_state.stack.backend.language == "python"
        assert len(saves) == 1

    def test_set_stack_invalid_template(self, empty_pipeline_state):
        """set_stack returns False for invalid template."""
        updater = StateUpdater(empty_pipeline_state, lambda s: None)

        result = updater.set_stack("invalid-template")

        assert result is False
        assert empty_pipeline_state.stack is None

    def test_set_stack_persists_to_yaml(self, temp_session_dir):
        """set_stack persists to project.yaml."""
        manager = PipelineStateManager(temp_session_dir)
        state = manager.initialize_pipeline_state()
        updater = StateUpdater(state, manager.save_pipeline_state)

        updater.set_stack("cli-python")

        # Reload and verify
        loaded = manager.load_pipeline_state()
        assert loaded.stack is not None
        assert loaded.stack.platform == "cli"
        assert loaded.stack.backend.framework == "typer"


# ========== Integration Tests ==========


class TestStackSelectionIntegration:
    """End-to-end tests for stack selection flow."""

    def test_notes_app_gets_web_stack(self, notes_app_mvp_spec, temp_session_dir):
        """Notes App flows to web-python-react stack."""
        # Detect platform
        platform, _ = recommend_platform(notes_app_mvp_spec)
        assert platform == "web_application"

        # Get default stack for platform
        stack_id = get_default_template_for_platform(platform)
        assert stack_id == "web-python-react"

        # Apply to state
        manager = PipelineStateManager(temp_session_dir)
        state = manager.initialize_pipeline_state()
        updater = StateUpdater(state, manager.save_pipeline_state)
        updater.set_stack(stack_id)

        # Verify
        loaded = manager.load_pipeline_state()
        assert loaded.stack.platform == "web_application"
        assert loaded.stack.backend.framework == "fastapi"
        assert loaded.stack.frontend.framework == "react"

    def test_full_presentation_flow(self, notes_app_mvp_spec):
        """Full flow from spec to presentation."""
        # Detect platform
        platform, scores = recommend_platform(notes_app_mvp_spec)

        # Get default stack
        stack_id = get_default_template_for_platform(platform)

        # Create presentation
        presentation = present_stack_choices(
            recommended_platform=platform,
            recommended_stack=stack_id,
            rationale="Notes App has dashboard and CRUD features",
        )

        # Verify presentation is complete
        assert presentation.recommended.template_id == stack_id
        assert "browser" in presentation.platform_explanation.lower()
        assert "[A]" in presentation.formatted_text
