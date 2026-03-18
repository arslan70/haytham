"""Shared utilities for Haytham evaluation framework."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
COMMANDS_DIR = ROOT / "commands"

# Default models for eval scripts. Short aliases for the claude CLI.
DEFAULT_GRADING_MODEL = "opus"
DEFAULT_CLASSIFICATION_MODEL = "sonnet"

# Maps full API model IDs to CLI aliases for backward compatibility.
_MODEL_ALIASES = {
    "claude-opus-4-20250514": "opus",
    "claude-opus-4-6-20260318": "opus",
    "claude-sonnet-4-20250514": "sonnet",
    "claude-sonnet-4-6-20260318": "sonnet",
    "claude-haiku-3-5-20241022": "haiku",
    "claude-haiku-4-5-20251001": "haiku",
}


def resolve_model(model: str) -> str:
    """Normalize a model name to a claude CLI alias."""
    return _MODEL_ALIASES.get(model, model)


def claude_call(user_prompt: str, system_prompt: str = "",
                model: str = DEFAULT_GRADING_MODEL,
                disable_tools: bool = True) -> str:
    """Call the claude CLI in print mode and return the response text.

    Uses the user's Claude Code subscription (no API key needed).
    Tools are disabled by default to prevent the CLI from loading plugins
    or executing commands when we just want text generation.
    """
    model = resolve_model(model)
    cmd = ["claude", "-p", "--model", model]
    if disable_tools:
        cmd.extend(["--tools", ""])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    try:
        result = subprocess.run(
            cmd, input=user_prompt, capture_output=True, text=True,
            timeout=300,
        )
    except FileNotFoundError:
        print("Error: 'claude' CLI not found. Install Claude Code or "
              "ensure 'claude' is on your PATH.", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    return result.stdout.strip()


def extract_json(text: str) -> dict | None:
    """Extract the first JSON object from LLM response text.

    Returns the parsed dict, or None if no valid JSON found.
    Tries progressively larger substrings starting from each '{' to
    handle braces inside quoted strings correctly.
    """
    pos = 0
    while pos < len(text):
        start = text.find("{", pos)
        if start == -1:
            return None
        # Try json.loads on substrings ending at each '}' from the end
        # Working backwards finds the correct closing brace efficiently
        for end in range(len(text) - 1, start, -1):
            if text[end] == "}":
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    continue
        pos = start + 1
    return None


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


def load_component_descriptions() -> dict:
    """Load name and description for all agents and commands.

    Returns a dict keyed by component name (agent name or command filename stem)
    with values containing 'type', 'name', and 'description'.
    """
    components = {}

    for agent_file in sorted(AGENTS_DIR.glob("*.md")):
        fm = parse_frontmatter(agent_file)
        name = fm.get("name", agent_file.stem)
        components[name] = {
            "type": "agent",
            "name": name,
            "description": fm.get("description", ""),
        }

    for cmd_file in sorted(COMMANDS_DIR.glob("*.md")):
        stem = cmd_file.stem
        fm = parse_frontmatter(cmd_file)
        components[stem] = {
            "type": "command",
            "name": stem,
            "description": fm.get("description", ""),
        }

    return components
