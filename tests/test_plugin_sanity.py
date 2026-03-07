"""Sanity tests for the Haytham Claude Code plugin.

Tests cover:
1. Frontmatter validation (agents + commands)
2. Script syntax checking (bash + python)
3. Cross-reference integrity (agents ↔ commands, hooks → scripts)
4. Schema validation logic (validate_schema.py pure functions)
5. Marketplace JSON validation
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
COMMANDS_DIR = ROOT / "commands"
SCRIPTS_DIR = ROOT / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

VALID_MODELS = {"sonnet", "opus", "haiku"}
VALID_HOOK_EVENTS = {"PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"}
VALID_CATEGORIES = {
    "development",
    "productivity",
    "security",
    "testing",
    "design",
    "database",
    "monitoring",
    "deployment",
    "learning",
}


def parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    frontmatter = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()
    return frontmatter


# ---------------------------------------------------------------------------
# 1. Frontmatter validation
# ---------------------------------------------------------------------------


class TestAgentFrontmatter:
    agents = list(AGENTS_DIR.glob("*.md"))

    @pytest.mark.parametrize("agent_file", agents, ids=lambda p: p.name)
    def test_has_name(self, agent_file):
        fm = parse_frontmatter(agent_file)
        assert "name" in fm, f"{agent_file.name} missing 'name' in frontmatter"

    @pytest.mark.parametrize("agent_file", agents, ids=lambda p: p.name)
    def test_has_description(self, agent_file):
        fm = parse_frontmatter(agent_file)
        assert (
            "description" in fm
        ), f"{agent_file.name} missing 'description' in frontmatter"

    @pytest.mark.parametrize("agent_file", agents, ids=lambda p: p.name)
    def test_has_model(self, agent_file):
        fm = parse_frontmatter(agent_file)
        assert "model" in fm, f"{agent_file.name} missing 'model' in frontmatter"

    @pytest.mark.parametrize("agent_file", agents, ids=lambda p: p.name)
    def test_valid_model(self, agent_file):
        fm = parse_frontmatter(agent_file)
        model = fm.get("model", "")
        assert model in VALID_MODELS, (
            f"{agent_file.name} has invalid model '{model}'. "
            f"Must be one of: {VALID_MODELS}"
        )

    @pytest.mark.parametrize("agent_file", agents, ids=lambda p: p.name)
    def test_has_tools(self, agent_file):
        fm = parse_frontmatter(agent_file)
        assert "tools" in fm, f"{agent_file.name} missing 'tools' in frontmatter"

    @pytest.mark.parametrize("agent_file", agents, ids=lambda p: p.name)
    def test_has_system_prompt(self, agent_file):
        text = agent_file.read_text()
        after_frontmatter = re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL)
        assert len(after_frontmatter.strip()) > 50, (
            f"{agent_file.name} has no substantial system prompt"
        )


class TestCommandFrontmatter:
    commands = list(COMMANDS_DIR.glob("*.md"))

    @pytest.mark.parametrize("cmd_file", commands, ids=lambda p: p.name)
    def test_has_description(self, cmd_file):
        fm = parse_frontmatter(cmd_file)
        assert (
            "description" in fm
        ), f"{cmd_file.name} missing 'description' in frontmatter"

    @pytest.mark.parametrize("cmd_file", commands, ids=lambda p: p.name)
    def test_has_allowed_tools(self, cmd_file):
        fm = parse_frontmatter(cmd_file)
        assert (
            "allowed-tools" in fm
        ), f"{cmd_file.name} missing 'allowed-tools' in frontmatter"


# ---------------------------------------------------------------------------
# 2. Script syntax checking
# ---------------------------------------------------------------------------


class TestScriptSyntax:
    def test_shell_scripts_parse(self):
        for sh_file in SCRIPTS_DIR.glob("*.sh"):
            result = subprocess.run(
                ["bash", "-n", str(sh_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"{sh_file.name} has bash syntax errors:\n{result.stderr}"
            )

    def test_python_scripts_compile(self):
        for py_file in SCRIPTS_DIR.glob("*.py"):
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"{py_file.name} has Python syntax errors:\n{result.stderr}"
            )


# ---------------------------------------------------------------------------
# 3. Cross-reference integrity
# ---------------------------------------------------------------------------


class TestCrossReferences:
    def _extract_agent_refs(self, command_path: Path) -> list[str]:
        """Extract agent names referenced in a command markdown file."""
        text = command_path.read_text()
        return re.findall(r"\*\*(\S+?)\*\* agent", text)

    def test_command_agent_refs_exist(self):
        """Every agent name referenced in commands has a matching agent file."""
        agent_files = {p.stem for p in AGENTS_DIR.glob("*.md")}
        missing = []
        for cmd_file in COMMANDS_DIR.glob("*.md"):
            for agent_name in self._extract_agent_refs(cmd_file):
                if agent_name not in agent_files:
                    missing.append(f"{cmd_file.name} references '{agent_name}' "
                                   f"but agents/{agent_name}.md does not exist")
        assert not missing, "\n".join(missing)

    def test_hook_script_paths_exist(self):
        """Every script path in hooks.json points to an existing file."""
        hooks_path = ROOT / "hooks" / "hooks.json"
        hooks = json.loads(hooks_path.read_text())
        missing = []
        for event, matchers in hooks.get("hooks", {}).items():
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    cmd = hook.get("command", "")
                    # Resolve ${CLAUDE_PLUGIN_ROOT} to repo root
                    resolved = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
                    # Strip the python3 prefix if present
                    parts = resolved.split()
                    script_path = parts[-1] if parts else resolved
                    if not os.path.isfile(script_path):
                        missing.append(
                            f"{event} hook references '{cmd}' but file not found"
                        )
        assert not missing, "\n".join(missing)

    def test_hook_event_names_valid(self):
        """Hook event names in hooks.json are valid Claude Code events."""
        hooks_path = ROOT / "hooks" / "hooks.json"
        hooks = json.loads(hooks_path.read_text())
        for event in hooks.get("hooks", {}).keys():
            assert event in VALID_HOOK_EVENTS, (
                f"Invalid hook event '{event}'. Must be one of: {VALID_HOOK_EVENTS}"
            )


# ---------------------------------------------------------------------------
# 4. Schema validation logic (testing pure functions from validate_schema.py
#    and validate_som.py)
# ---------------------------------------------------------------------------


# Import the validation functions by adding scripts/ to path
sys.path.insert(0, str(SCRIPTS_DIR))
from validate_schema import validate_file
from validate_som import (
    validate_regulated_domain_safety,
    validate_som_arithmetic,
)


class TestSchemaValidation:
    def test_valid_validation_report(self, tmp_path):
        src = FIXTURES_DIR / "valid_validation_report.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_validation_report(self, tmp_path):
        src = FIXTURES_DIR / "invalid_validation_report.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("Invalid recommendation" in w for w in warnings)
        assert any("Missing/empty executive_summary" in w for w in warnings)

    def test_valid_capabilities(self, tmp_path):
        src = FIXTURES_DIR / "valid_capabilities.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_capabilities_missing_traceability(self, tmp_path):
        src = FIXTURES_DIR / "invalid_capabilities.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("no serves_scope_item" in w for w in warnings)

    def test_invalid_capabilities_bad_flow(self, tmp_path):
        src = FIXTURES_DIR / "invalid_capabilities.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("invalid flow ref" in w for w in warnings)

    def test_valid_stories(self, tmp_path):
        src = FIXTURES_DIR / "valid_stories.json"
        dst = tmp_path / ".haytham" / "session" / "phase-4-stories" / "stories.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_stories_broken_dependency(self, tmp_path):
        src = FIXTURES_DIR / "invalid_stories.json"
        dst = tmp_path / ".haytham" / "session" / "phase-4-stories" / "stories.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("doesn't exist" in w for w in warnings)

    def test_non_session_file_skipped(self, tmp_path):
        dst = tmp_path / "random.json"
        dst.write_text('{"foo": "bar"}')
        warnings = validate_file(str(dst))
        assert not warnings

    def test_non_json_file_skipped(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "report.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("# Report")
        warnings = validate_file(str(dst))
        assert not warnings


class TestSomValidation:
    def test_consistent_som_no_warnings(self):
        text = "The SOM is $5M. Based on our analysis, the SOM of $5M is achievable."
        assert validate_som_arithmetic(text) == []

    def test_mismatched_som_warns(self):
        text = "The SOM is $5M in one section. The SOM is $50M in another."
        warnings = validate_som_arithmetic(text)
        assert len(warnings) == 1
        assert "mismatch" in warnings[0]

    def test_single_som_no_warning(self):
        text = "The SOM is $5M."
        assert validate_som_arithmetic(text) == []

    def test_regulated_domain_hipaa(self):
        warnings = validate_regulated_domain_safety(
            report_text="The market looks good.",
            idea_text="A mental health therapy app",
            recommendation="GO",
        )
        assert any("HIPAA" in w for w in warnings)

    def test_regulated_domain_present(self):
        warnings = validate_regulated_domain_safety(
            report_text="HIPAA compliance is critical for this market.",
            idea_text="A mental health therapy app",
            recommendation="GO",
        )
        # HIPAA is mentioned, so no "missing" warning, but GO + regulatory triggers a review warning
        assert not any("does not mention HIPAA" in w for w in warnings)

    def test_go_with_regulatory_warns(self):
        warnings = validate_regulated_domain_safety(
            report_text="HIPAA and PCI-DSS compliance required.",
            idea_text="A health payment app",
            recommendation="GO",
        )
        assert any("GO recommendation with regulatory" in w for w in warnings)

    def test_nogo_with_regulatory_no_extra_warning(self):
        warnings = validate_regulated_domain_safety(
            report_text="HIPAA compliance required.",
            idea_text="A health app",
            recommendation="NO-GO",
        )
        assert not any("GO recommendation" in w for w in warnings)


# ---------------------------------------------------------------------------
# 5. Marketplace JSON validation
# ---------------------------------------------------------------------------


class TestMarketplaceJson:
    def test_plugin_json_valid(self):
        path = ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text())
        assert "name" in data
        assert "description" in data

    def test_marketplace_json_valid(self):
        path = ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text())
        assert "$schema" in data
        assert "name" in data
        assert "plugins" in data
        assert len(data["plugins"]) > 0

    def test_marketplace_plugin_has_required_fields(self):
        path = ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text())
        for plugin in data["plugins"]:
            assert "name" in plugin
            assert "description" in plugin
            assert "source" in plugin

    def test_marketplace_category_valid(self):
        path = ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text())
        for plugin in data["plugins"]:
            category = plugin.get("category")
            if category:
                assert category in VALID_CATEGORIES, (
                    f"Invalid category '{category}'. "
                    f"Must be one of: {VALID_CATEGORIES}"
                )
