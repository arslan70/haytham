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

    def test_invalid_capabilities_bad_flow_part(self, tmp_path):
        src = FIXTURES_DIR / "invalid_capabilities_bad_flow_part.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("invalid flow ref" in w and "Flow 99" in w for w in warnings)
        # Flow 1 part should NOT trigger a warning
        assert not any("Flow 1" in w for w in warnings)

    def test_valid_concept_anchor(self, tmp_path):
        src = FIXTURES_DIR / "valid_concept_anchor.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_concept_anchor_enums(self, tmp_path):
        src = FIXTURES_DIR / "invalid_concept_anchor.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("technical_level" in w for w in warnings)
        assert any("domain_expertise" in w for w in warnings)
        assert any("business_model" in w for w in warnings)
        assert any("success_metric" in w for w in warnings)
        assert any("distribution" in w for w in warnings)

    def test_invalid_concept_anchor_founder_intent(self, tmp_path):
        src = FIXTURES_DIR / "invalid_concept_anchor.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("founder_intent.motivation" in w and "vibes" in w for w in warnings)
        assert any("time_horizon" in w and "eons" in w for w in warnings)
        assert any("constraints.team" in w and "army" in w for w in warnings)

    def test_invalid_concept_anchor_growth_model(self, tmp_path):
        src = FIXTURES_DIR / "invalid_concept_anchor.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("growth_model" in w and "teleportation" in w for w in warnings)

    def test_valid_validation_report_with_new_fields(self, tmp_path):
        src = FIXTURES_DIR / "valid_validation_report.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_validation_report_bad_path(self, tmp_path):
        src = FIXTURES_DIR / "invalid_validation_report.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("recommended_path" in w and "vibes_based" in w for w in warnings)

    def test_invalid_validation_report_bad_positioning(self, tmp_path):
        src = FIXTURES_DIR / "invalid_validation_report.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("defensibility" in w and "impenetrable" in w for w in warnings)
        assert any("founder_market_fit" in w and "legendary" in w for w in warnings)

    def test_invalid_validation_report_bad_assumptions(self, tmp_path):
        src = FIXTURES_DIR / "invalid_validation_report.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("assumptions[0].claim" in w and "Missing/empty" in w for w in warnings)
        assert any("evidence_level" in w and "guessing" in w for w in warnings)

    def test_valid_founder_corrections(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "founder-corrections.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(json.dumps({
            "corrections": [
                {"dimension": "competition", "correction": "We complement X, not compete"},
                {"dimension": "business_model", "correction": "Open source, not SaaS"}
            ],
            "updated_at": "2026-03-09T12:00:00Z"
        }))
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_founder_corrections(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "founder-corrections.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(json.dumps({
            "corrections": [
                {"dimension": "vibes", "correction": "We're chill"},
                {"dimension": "competition", "correction": ""}
            ],
            "updated_at": "2026-03-09T12:00:00Z"
        }))
        warnings = validate_file(str(dst))
        assert any("dimension" in w and "vibes" in w for w in warnings)
        assert any("correction" in w and "empty" in w.lower() for w in warnings)

    def test_valid_system_traits(self, tmp_path):
        src = FIXTURES_DIR / "valid_system_traits.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "system-traits.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_system_traits_boolean_explanation(self, tmp_path):
        src = FIXTURES_DIR / "invalid_system_traits.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "system-traits.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("realtime" in w and "not a string" in w for w in warnings)

    def test_invalid_system_traits_unknown_trait(self, tmp_path):
        src = FIXTURES_DIR / "invalid_system_traits_unknown.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "system-traits.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("telepathy" in w and "Unknown trait" in w for w in warnings)

    def test_valid_build_buy(self, tmp_path):
        src = FIXTURES_DIR / "valid_build_buy.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "build-buy.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_build_buy_bad_category(self, tmp_path):
        src = FIXTURES_DIR / "invalid_build_buy.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "build-buy.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("orchestration" in w and "Custom infrastructure" in w for w in warnings)

    def test_invalid_build_buy_bad_recommendation(self, tmp_path):
        src = FIXTURES_DIR / "invalid_build_buy.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "build-buy.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("MAGIC" in w and "recommendation" in w for w in warnings)

    def test_capabilities_mega_capability_detected(self, tmp_path):
        src = FIXTURES_DIR / "capabilities_mega.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("multiple scope items" in w for w in warnings)

    def test_capabilities_count_mismatch(self, tmp_path):
        src = FIXTURES_DIR / "capabilities_count_mismatch.json"
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("Fewer capabilities" in w and "scope items" in w for w in warnings)

    def test_capabilities_over_decomposition(self, tmp_path):
        """Warn when capability count exceeds 4x scope items."""
        data = {
            "summary": {"system_name": "T", "system_purpose": "T",
                         "primary_user_segment": "T", "input_method": "M",
                         "mvp_scope_respected": True},
            "capabilities": {
                "functional": [
                    {"id": f"CAP-F-{i:03d}", "name": f"F{i}", "description": "D",
                     "serves_scope_item": "S", "user_flow": "Flow 1",
                     "acceptance_criteria": ["OK"], "rationale": "OK"}
                    for i in range(1, 22)
                ],
                "non_functional": []
            },
            "traceability": {"scope_items_covered": ["A", "B", "C", "D", "E"],
                             "scope_items_not_covered": [],
                             "flows_covered": ["Flow 1"]},
            "metadata": {"functional_count": 21, "non_functional_count": 0}
        }
        dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(json.dumps(data))
        warnings = validate_file(str(dst))
        assert any("more than 4x" in w for w in warnings)

    def test_valid_arch_decisions(self, tmp_path):
        src = FIXTURES_DIR / "valid_arch_decisions.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "architecture-decisions.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_arch_decisions_uncovered(self, tmp_path):
        src = FIXTURES_DIR / "arch_decisions_uncovered.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "architecture-decisions.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("uncovered capabilities" in w for w in warnings)

    def test_arch_decisions_bad_id_format(self, tmp_path):
        src = FIXTURES_DIR / "arch_decisions_bad_id.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "architecture-decisions.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        # DEC-BANANA-001 has valid format but non-standard category
        assert any("BANANA" in w and "Custom decision category" in w for w in warnings)
        # DECISION-DB-1 has invalid format entirely
        assert any("Invalid decision ID format" in w and "DECISION-DB-1" in w for w in warnings)

    def test_arch_decisions_cross_check_no_caps_file(self, tmp_path):
        """Cross-check gracefully skips when capabilities.json doesn't exist."""
        src = FIXTURES_DIR / "valid_arch_decisions.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "architecture-decisions.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        # No phase-2-what/capabilities.json created
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_arch_decisions_coverage_cross_check(self, tmp_path):
        # Set up capabilities.json in phase-2-what
        caps_src = FIXTURES_DIR / "capabilities_for_cross_check.json"
        caps_dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        caps_dst.parent.mkdir(parents=True)
        caps_dst.write_text(caps_src.read_text())
        # Set up architecture-decisions.json in phase-3-how (claims coverage of F-001, F-002 only)
        arch_src = FIXTURES_DIR / "arch_decisions_coverage_mismatch.json"
        arch_dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "architecture-decisions.json"
        arch_dst.parent.mkdir(parents=True)
        arch_dst.write_text(arch_src.read_text())
        warnings = validate_file(str(arch_dst))
        # Should detect CAP-F-003 and CAP-NF-001 are missing from coverage_check
        assert any("CAP-F-003" in w for w in warnings)
        assert any("CAP-NF-001" in w for w in warnings)

    def test_valid_scope_risk(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(json.dumps({
            "archetype": "developer_tool",
            "intent": {"goal": "Build a tool", "explicit_constraints": [], "non_goals": []},
            "invariants": [
                {"property": "access_model", "value": "open", "source": "stated",
                 "confidence": 0.9, "scope_risk": "high"},
                {"property": "interaction_model", "value": "cli", "source": "stated",
                 "confidence": 0.9, "scope_risk": "low"},
                {"property": "session_medium", "value": "terminal", "source": "stated",
                 "confidence": 0.9},
            ],
            "identity": {"features": ["Fast"], "why_distinctive": "Speed"},
            "founder_profile": {"technical_level": "technical", "domain_expertise": "high",
                                "inference_basis": "Describes architecture"},
            "strategic_signals": {"business_model": "open-source", "success_metric": "community_adoption",
                                  "distribution": "standalone", "inference_notes": "Explicit"},
        }))
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_valid_concept_anchor_with_term_flags(self, tmp_path):
        src = FIXTURES_DIR / "valid_concept_anchor_with_term_flags.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_term_flags_missing_fields(self, tmp_path):
        src = FIXTURES_DIR / "invalid_concept_anchor_term_flags.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        # Empty required fields on first flag
        assert any("term_flags[0].term" in w and "Missing/empty" in w for w in warnings)
        assert any("term_flags[0].chosen_interpretation" in w for w in warnings)
        # Empty alternatives array
        assert any("term_flags[0].alternatives" in w and "non-empty array" in w for w in warnings)

    def test_invalid_term_flags_bad_invariant_refs(self, tmp_path):
        src = FIXTURES_DIR / "invalid_concept_anchor_term_flags.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("nonexistent_property" in w and "not in invariants" in w for w in warnings)

    def test_term_flags_consistency_low_confidence_unflagged(self, tmp_path):
        src = FIXTURES_DIR / "invalid_concept_anchor_term_flags.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        # interaction_model has confidence 0.6 but no term_flags entry references it
        assert any("interaction_model" in w and "confidence < 0.7" in w for w in warnings)

    def test_term_flags_absent_is_valid(self, tmp_path):
        """Concept anchor without term_flags field is still valid."""
        src = FIXTURES_DIR / "valid_concept_anchor.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_scope_risk(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(json.dumps({
            "archetype": "developer_tool",
            "intent": {"goal": "Build a tool", "explicit_constraints": [], "non_goals": []},
            "invariants": [
                {"property": "access_model", "value": "open", "source": "stated",
                 "confidence": 0.9, "scope_risk": "extreme"},
            ],
            "identity": {"features": ["Fast"], "why_distinctive": "Speed"},
        }))
        warnings = validate_file(str(dst))
        assert any("scope_risk" in w and "extreme" in w for w in warnings)

    def test_uvp_validation_valid(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "idea-analysis.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("## 1. Problem Analysis\n\nStuff.\n\n"
                       "## 2. Target User Segments\n\nSegments.\n\n"
                       "## 3. Unique Value Proposition\n\n"
                       "Solo builders can go from idea to spec in under 10 minutes.\n\n"
                       "## 4. Solution Concept\n\nConcept.")
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_uvp_validation_too_long(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "idea-analysis.md"
        dst.parent.mkdir(parents=True)
        long_uvp = "A" * 141
        dst.write_text(f"## 3. Unique Value Proposition\n\n{long_uvp}\n\n## 4. Solution Concept")
        warnings = validate_file(str(dst))
        assert any("exceeds 140 chars" in w for w in warnings)

    def test_uvp_validation_missing_format(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "idea-analysis.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("## 3. Unique Value Proposition\n\nJust a random statement here.\n\n## 4. Solution Concept")
        warnings = validate_file(str(dst))
        assert any("does not match" in w for w in warnings)

    def test_valid_research_directives(self, tmp_path):
        src = FIXTURES_DIR / "valid_research_directives.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "research-directives.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_invalid_research_directives_bad_classification(self, tmp_path):
        src = FIXTURES_DIR / "invalid_research_directives.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "research-directives.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("telekinetic" in w and "invalid classification" in w for w in warnings)

    def test_invalid_research_directives_empty_questions(self, tmp_path):
        src = FIXTURES_DIR / "invalid_research_directives.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "research-directives.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("research_required is true but questions is empty" in w for w in warnings)

    def test_invalid_research_directives_standard_mixed(self, tmp_path):
        src = FIXTURES_DIR / "invalid_research_directives.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "research-directives.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("'standard' classification must be exclusive" in w for w in warnings)

    def test_invalid_research_directives_summary_mismatch(self, tmp_path):
        src = FIXTURES_DIR / "invalid_research_directives.json"
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "research-directives.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert any("summary.total (99) does not match" in w for w in warnings)
        assert any("summary.requiring_research (99) does not match" in w for w in warnings)

    def test_research_directives_cross_check(self, tmp_path):
        """Cross-check: directives reference valid capabilities, all CAP-F-* covered."""
        caps_dst = tmp_path / ".haytham" / "session" / "phase-2-what" / "capabilities.json"
        caps_dst.parent.mkdir(parents=True)
        caps_dst.write_text(json.dumps({
            "summary": {"system_name": "T", "system_purpose": "T",
                        "primary_user_segment": "T", "input_method": "T",
                        "mvp_scope_respected": True},
            "capabilities": {
                "functional": [
                    {"id": "CAP-F-001", "name": "A", "description": "A",
                     "serves_scope_item": "X", "user_flow": "Flow 1",
                     "acceptance_criteria": ["OK"], "rationale": "OK"},
                    {"id": "CAP-F-002", "name": "B", "description": "B",
                     "serves_scope_item": "Y", "user_flow": "Flow 1",
                     "acceptance_criteria": ["OK"], "rationale": "OK"},
                ],
                "non_functional": []
            },
            "traceability": {"scope_items_covered": ["X", "Y"],
                             "scope_items_not_covered": [], "flows_covered": ["Flow 1"]},
            "metadata": {"functional_count": 2, "non_functional_count": 0}
        }))
        # Directives only cover CAP-F-001 and reference a nonexistent CAP-F-999
        dst = tmp_path / ".haytham" / "session" / "phase-3-how" / "research-directives.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(json.dumps({
            "directives": [
                {"capability_id": "CAP-F-001", "capability_name": "A",
                 "classifications": ["standard"], "research_required": False, "questions": []},
                {"capability_id": "CAP-F-999", "capability_name": "Ghost",
                 "classifications": ["standard"], "research_required": False, "questions": []},
            ],
            "summary": {"total": 2, "requiring_research": 0}
        }))
        warnings = validate_file(str(dst))
        assert any("CAP-F-999" in w and "does not exist" in w for w in warnings)
        assert any("CAP-F-002" in w and "missing" in w.lower() for w in warnings)

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


class TestOpenSpecValidation:
    def test_valid_openspec(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate_openspec.py"),
             str(FIXTURES_DIR / "valid_openspec")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Unexpected warnings: {result.stderr}"

    def test_valid_openspec_with_coverage(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate_openspec.py"),
             str(FIXTURES_DIR / "valid_openspec"),
             str(FIXTURES_DIR / "openspec_capabilities.json")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Unexpected warnings: {result.stderr}"

    def test_invalid_openspec_bad_shall(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate_openspec.py"),
             str(FIXTURES_DIR / "invalid_openspec")],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "SHALL grammar" in result.stderr

    def test_invalid_openspec_missing_traits(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate_openspec.py"),
             str(FIXTURES_DIR / "invalid_openspec")],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "traits" in result.stderr

    def test_invalid_openspec_missing_project_sections(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate_openspec.py"),
             str(FIXTURES_DIR / "invalid_openspec")],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "Project Structure" in result.stderr

    def test_duplicate_capabilities_detected(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate_openspec.py"),
             str(FIXTURES_DIR / "openspec_duplicate_caps")],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "Duplicate capability" in result.stderr
        assert "CAP-F-001" in result.stderr


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
# 4b. New eval coverage: markdown validation, concept anchor completeness,
#     multi-archetype fixtures, cross-file checks
# ---------------------------------------------------------------------------


class TestValidationReportMarkdown:
    """E1, E2, E3: Validate validation-report.md structure."""

    def test_all_sections_present(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.md"
        dst.parent.mkdir(parents=True)
        dst.write_text(
            "# Validation Report\n\n"
            "## 1. The Opportunity\nContent\n\n"
            "## 2. Competitive Landscape\nContent\n\n"
            "## 3. Claims & Evidence\nContent\n\n"
            "## 4. Risk Profile\nDealbreaker Check: yes\n\n"
            "## 5. Financial Feasibility\nContent\n\n"
            "## 6. Our Recommendation\n**Composite Score:** 3.2/5.0\n\n"
            "## 7. Validate Before You Build\nContent\n\n"
            "## 8. Next Steps\nContent\n\n"
            "## 9. Positioning Analysis\nContent\n\n"
            "## 10. Strategic Options\nContent\n\n"
            "## 11. Assumptions & Evidence\nContent\n"
        )
        warnings = validate_file(str(dst))
        assert not warnings, f"Unexpected warnings: {warnings}"

    def test_missing_section_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.md"
        dst.parent.mkdir(parents=True)
        # Missing sections 9, 10, 11
        dst.write_text(
            "# Validation Report\n\n"
            "## 1. The Opportunity\nContent\n\n"
            "## 2. Competitive Landscape\nContent\n\n"
            "## 3. Claims & Evidence\nContent\n\n"
            "## 4. Risk Profile\nDealbreaker Check: yes\n\n"
            "## 5. Financial Feasibility\nContent\n\n"
            "## 6. Our Recommendation\n**Composite Score:** 3.2/5.0\n\n"
            "## 7. Validate Before You Build\nContent\n\n"
            "## 8. Next Steps\nContent\n"
        )
        warnings = validate_file(str(dst))
        assert any("9. Positioning" in w for w in warnings)
        assert any("10. Strategic" in w for w in warnings)
        assert any("11. Assumptions" in w for w in warnings)

    def test_missing_composite_score_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("# Validation Report\n\n## 6. Our Recommendation\nNo score here.\n")
        warnings = validate_file(str(dst))
        assert any("Composite Score" in w for w in warnings)

    def test_missing_dealbreaker_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "validation-report.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("# Validation Report\n\n## 4. Risk Profile\nNo check here.\n")
        warnings = validate_file(str(dst))
        assert any("Dealbreaker" in w for w in warnings)


class TestConceptAnchorCompleteness:
    """E4, E5, E6: Required invariants, confidence range, term flags cap."""

    def test_required_invariants_present(self, tmp_path):
        src = FIXTURES_DIR / "valid_concept_anchor.json"
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        # Valid fixture has all three required invariants
        assert not any("Missing required invariant" in w for w in warnings)

    def test_missing_required_invariant_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        data = json.loads((FIXTURES_DIR / "valid_concept_anchor.json").read_text())
        # Remove session_medium
        data["invariants"] = [
            inv for inv in data["invariants"]
            if inv.get("property") != "session_medium"
        ]
        dst.write_text(json.dumps(data))
        warnings = validate_file(str(dst))
        assert any("session_medium" in w for w in warnings)

    def test_confidence_out_of_range_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        data = json.loads((FIXTURES_DIR / "valid_concept_anchor.json").read_text())
        data["invariants"][0]["confidence"] = 1.5
        dst.write_text(json.dumps(data))
        warnings = validate_file(str(dst))
        assert any("confidence 1.5" in w for w in warnings)

    def test_term_flags_cap_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        data = json.loads((FIXTURES_DIR / "valid_concept_anchor.json").read_text())
        flag = {
            "term": "test",
            "chosen_interpretation": "A",
            "alternatives": ["B"],
            "impact": "Changes archetype",
        }
        data["term_flags"] = [flag, flag, flag, flag]  # 4 flags, exceeds cap
        dst.write_text(json.dumps(data))
        warnings = validate_file(str(dst))
        assert any("Hard cap is 3" in w for w in warnings)


class TestResearchBriefTone:
    """E7: Banned judgment language in research brief."""

    def test_no_judgment_language_clean(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "research-brief.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("# Research Brief\n\nThe market has 500 users.\n")
        warnings = validate_file(str(dst))
        assert not any("Banned judgment" in w for w in warnings)

    def test_judgment_language_flagged(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "research-brief.md"
        dst.parent.mkdir(parents=True)
        dst.write_text("# Research Brief\n\nThis is a promising market with strong growth.\n")
        warnings = validate_file(str(dst))
        assert any("promising" in w for w in warnings)
        assert any("strong" in w for w in warnings)

    def test_word_boundary_no_false_positive(self, tmp_path):
        """Substrings like 'armstrong' or 'stronger' should not trigger 'strong'."""
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "research-brief.md"
        dst.parent.mkdir(parents=True)
        dst.write_text(
            "# Research Brief\n\n"
            "Armstrong Industries has 500 users.\n"
            "The stronger competitor has 1000 users.\n"
        )
        warnings = validate_file(str(dst))
        assert not any("Banned judgment" in w for w in warnings)


class TestMarketResearchStructure:
    """E8: Trend count and counter-trend check."""

    def test_three_trends_with_counter(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "market-research.md"
        dst.parent.mkdir(parents=True)
        dst.write_text(
            "# Market Research\n\n"
            "#### 4. Market Trends\n\n"
            "**Trend 1 (tailwind):** Growth.\n\n"
            "**Trend 2 (tailwind):** More growth.\n\n"
            "**Trend 3 (counter-trend):** Decline.\n\n"
            "#### 5. Market Risks\n\nRisks here.\n"
        )
        warnings = validate_file(str(dst))
        assert not any("trends" in w.lower() for w in warnings)
        assert not any("counter-trend" in w.lower() for w in warnings)

    def test_wrong_trend_count_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "market-research.md"
        dst.parent.mkdir(parents=True)
        dst.write_text(
            "# Market Research\n\n"
            "#### 4. Market Trends\n\n"
            "**Trend 1:** Growth.\n\n"
            "**Trend 2:** More growth.\n\n"
            "#### 5. Market Risks\n\nRisks here.\n"
        )
        warnings = validate_file(str(dst))
        assert any("2 trends" in w for w in warnings)


class TestWordBudgetWarnings:
    """E9: Word budget checks fire for over-budget sections."""

    def test_market_research_over_budget_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "market-research.md"
        dst.parent.mkdir(parents=True)
        # Section 5 budget is 100 words, 25% tolerance = 125. Write 130 words.
        filler = " ".join(["risk"] * 130)
        dst.write_text(
            "# Market Research\n\n"
            "#### 5. Market Risks\n\n"
            f"{filler}\n"
        )
        warnings = validate_file(str(dst))
        assert any("5. Market Risks" in w and "words" in w for w in warnings)

    def test_market_research_within_budget_no_warning(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "market-research.md"
        dst.parent.mkdir(parents=True)
        # Section 5 budget is 100 words, write 90 (within budget)
        filler = " ".join(["risk"] * 90)
        dst.write_text(
            "# Market Research\n\n"
            "#### 5. Market Risks\n\n"
            f"{filler}\n"
        )
        warnings = validate_file(str(dst))
        assert not any("5. Market Risks" in w for w in warnings)

    def test_competitor_research_over_budget_warns(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "competitor-research.md"
        dst.parent.mkdir(parents=True)
        # Section 1 budget is 300 words, 25% tolerance = 375. Write 400 words.
        filler = " ".join(["competitor"] * 400)
        dst.write_text(
            "# Competitor Research\n\n"
            "### 1. Competitor Identification\n\n"
            f"{filler}\n\n"
            "### 2. User Sentiment\n\nShort.\n"
        )
        warnings = validate_file(str(dst))
        assert any("1. Competitor ID" in w and "words" in w for w in warnings)

    def test_competitor_research_within_budget_no_warning(self, tmp_path):
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "competitor-research.md"
        dst.parent.mkdir(parents=True)
        # Section 1 budget is 300 words, write 250 (within budget)
        filler = " ".join(["competitor"] * 250)
        dst.write_text(
            "# Competitor Research\n\n"
            "### 1. Competitor Identification\n\n"
            f"{filler}\n\n"
            "### 2. User Sentiment\n\nShort.\n"
        )
        warnings = validate_file(str(dst))
        assert not any("1. Competitor ID" in w for w in warnings)

    def test_word_budget_includes_sub_headings(self, tmp_path):
        """Sub-headings within a section should be counted in the parent's word budget."""
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "market-research.md"
        dst.parent.mkdir(parents=True)
        # Section 2 (JTBD) budget is 150, tolerance 187. Write 200 words
        # split across sub-headings within the section.
        filler_a = " ".join(["job"] * 100)
        filler_b = " ".join(["task"] * 100)
        dst.write_text(
            "# Market Research\n\n"
            "#### 2. Jobs-to-be-Done\n\n"
            "**A. Core Jobs**\n\n"
            f"{filler_a}\n\n"
            "**B. Job Dimensions**\n\n"
            f"{filler_b}\n\n"
            "#### 3. Market Size\n\nSmall.\n"
        )
        warnings = validate_file(str(dst))
        assert any("2. JTBD" in w and "words" in w for w in warnings)


class TestEvidenceTagPreservation:
    """E11: Evidence tags in research brief should match upstream sources."""

    def test_mismatched_tag_warns(self, tmp_path):
        phase_dir = tmp_path / ".haytham" / "session" / "phase-1-why"
        phase_dir.mkdir(parents=True)

        # Upstream has [Verified: Statista]
        (phase_dir / "market-research.md").write_text(
            "# Market Research\n\nTAM is $5B [Verified: Statista]\n"
        )
        (phase_dir / "competitor-research.md").write_text(
            "# Competitor Research\n\nCompetitor has 1000 users [Verified: Crunchbase]\n"
        )
        # Brief changes the tag source
        brief_path = phase_dir / "research-brief.md"
        brief_path.write_text(
            "# Research Brief\n\nTAM is $5B [Verified: IBISWorld]\n"
            "Competitor has 1000 users [Verified: Crunchbase]\n"
        )
        warnings = validate_file(str(brief_path))
        assert any("tag mismatch" in w.lower() or "evidence tag" in w.lower() for w in warnings)

    def test_preserved_tags_no_warning(self, tmp_path):
        phase_dir = tmp_path / ".haytham" / "session" / "phase-1-why"
        phase_dir.mkdir(parents=True)

        (phase_dir / "market-research.md").write_text(
            "# Market Research\n\nTAM is $5B [Verified: Statista]\n"
        )
        (phase_dir / "competitor-research.md").write_text(
            "# Competitor Research\n\nCompetitor has 1000 users [Verified: Crunchbase]\n"
        )
        # Brief preserves exact tags
        brief_path = phase_dir / "research-brief.md"
        brief_path.write_text(
            "# Research Brief\n\nTAM is $5B [Verified: Statista]\n"
            "Competitor has 1000 users [Verified: Crunchbase]\n"
        )
        warnings = validate_file(str(brief_path))
        assert not any("tag mismatch" in w.lower() or "evidence tag" in w.lower() for w in warnings)

    def test_dropped_upstream_tag_warns(self, tmp_path):
        """Brief that omits an upstream evidence tag should warn about lost evidence."""
        phase_dir = tmp_path / ".haytham" / "session" / "phase-1-why"
        phase_dir.mkdir(parents=True)

        (phase_dir / "market-research.md").write_text(
            "# Market Research\n\nTAM is $5B [Verified: Statista]\n"
        )
        (phase_dir / "competitor-research.md").write_text(
            "# Competitor Research\n\nCompetitor has 1000 users [Verified: Crunchbase]\n"
        )
        # Brief only includes one of the two upstream tags
        brief_path = phase_dir / "research-brief.md"
        brief_path.write_text(
            "# Research Brief\n\nTAM is $5B [Verified: Statista]\n"
        )
        warnings = validate_file(str(brief_path))
        assert any("not preserved" in w and "Crunchbase" in w for w in warnings)


class TestMultiArchetypeFixtures:
    """E10: All archetype fixtures pass validation."""

    @pytest.mark.parametrize("fixture_name", [
        "valid_concept_anchor.json",
        "valid_concept_anchor_consumer.json",
        "valid_concept_anchor_marketplace.json",
        "valid_concept_anchor_b2b.json",
    ], ids=lambda p: p.replace(".json", ""))
    def test_archetype_fixture_valid(self, fixture_name, tmp_path):
        src = FIXTURES_DIR / fixture_name
        dst = tmp_path / ".haytham" / "session" / "phase-1-why" / "concept-anchor.json"
        dst.parent.mkdir(parents=True)
        dst.write_text(src.read_text())
        warnings = validate_file(str(dst))
        assert not warnings, f"Warnings for {fixture_name}: {warnings}"


class TestCompositeScoreConsistency:
    """E2: Cross-file composite score check (JSON vs markdown)."""

    def test_matching_scores_no_warning(self, tmp_path):
        phase_dir = tmp_path / ".haytham" / "session" / "phase-1-why"
        phase_dir.mkdir(parents=True)

        md_path = phase_dir / "validation-report.md"
        md_path.write_text("## 6. Our Recommendation\n**Composite Score:** 3.2/5.0\n")

        json_data = json.loads((FIXTURES_DIR / "valid_validation_report.json").read_text())
        json_data["composite_score"] = 3.2
        json_path = phase_dir / "validation-report.json"
        json_path.write_text(json.dumps(json_data))

        warnings = validate_file(str(json_path))
        assert not any("Composite score mismatch" in w for w in warnings)

    def test_mismatched_scores_warns(self, tmp_path):
        phase_dir = tmp_path / ".haytham" / "session" / "phase-1-why"
        phase_dir.mkdir(parents=True)

        md_path = phase_dir / "validation-report.md"
        md_path.write_text("## 6. Our Recommendation\n**Composite Score:** 3.5/5.0\n")

        json_data = json.loads((FIXTURES_DIR / "valid_validation_report.json").read_text())
        json_data["composite_score"] = 2.8
        json_path = phase_dir / "validation-report.json"
        json_path.write_text(json.dumps(json_data))

        warnings = validate_file(str(json_path))
        assert any("Composite score mismatch" in w for w in warnings)


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

    def test_version_single_source_of_truth(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        assert "version" not in plugin, (
            "plugin.json must NOT carry a version field. "
            "Claude Code reads the plugin version from marketplace.json; "
            "duplicating it here creates a sync bug class."
        )
        assert "version" in marketplace["plugins"][0], (
            "marketplace.json plugins[0] must have a version field"
        )
