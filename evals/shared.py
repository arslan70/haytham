"""Shared utilities for Haytham evaluation framework."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
COMMANDS_DIR = ROOT / "commands"


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
