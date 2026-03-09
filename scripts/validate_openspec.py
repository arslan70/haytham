#!/usr/bin/env python3
"""Validate a complete OpenSpec directory.

Usage:
    validate_openspec.py <openspec_dir> [capabilities.json]

Checks:
1. config.yaml exists and has required keys
2. project.md exists and has required sections
3. At least one specs/*/spec.md exists
4. specs/cross-cutting/spec.md exists
5. SHALL grammar uses bare infinitive verbs
6. Gherkin completeness (Given/When/Then in every Scenario)
7. (Optional) Coverage: every CAP-F-* and CAP-NF-* from capabilities.json
   appears in at least one spec file

Exits 0 on success, 1 with warnings on failure.
"""

import json
import os
import re
import sys
from pathlib import Path

# Known bad third-person verbs after SHALL. A suffix-based rule (rejecting
# words ending in -s) would false-positive on bare infinitives like "process",
# "address", "access".
BAD_SHALL_VERBS = {
    "ensures",
    "provides",
    "handles",
    "validates",
    "manages",
    "supports",
    "maintains",
    "performs",
    "creates",
    "returns",
    "displays",
    "requires",
    "allows",
    "enables",
}

REQUIRED_CONFIG_KEYS = {"name", "description", "appetite", "traits", "generated_at"}
REQUIRED_PROJECT_SECTIONS = {"## Tech Stack", "## Architecture Decisions"}


def parse_yaml_keys(text: str) -> set[str]:
    """Extract top-level YAML keys using regex (no pyyaml dependency)."""
    keys = set()
    for line in text.splitlines():
        match = re.match(r"^([a-z_][a-z_0-9]*):", line)
        if match:
            keys.add(match.group(1))
    return keys


def validate_config(openspec_dir: Path) -> list[str]:
    """Validate config.yaml exists and has required keys."""
    warnings = []
    config_path = openspec_dir / "config.yaml"
    if not config_path.is_file():
        warnings.append("Missing config.yaml")
        return warnings

    text = config_path.read_text()

    # Try yaml.safe_load first, fall back to regex
    config_keys: set[str] = set()
    try:
        import yaml

        data = yaml.safe_load(text)
        if isinstance(data, dict):
            config_keys = set(data.keys())
    except (ImportError, Exception):
        config_keys = parse_yaml_keys(text)

    missing = REQUIRED_CONFIG_KEYS - config_keys
    for key in sorted(missing):
        warnings.append(f"config.yaml missing required key: {key}")

    return warnings


def validate_project(openspec_dir: Path) -> list[str]:
    """Validate project.md exists and has required sections."""
    warnings = []
    project_path = openspec_dir / "project.md"
    if not project_path.is_file():
        warnings.append("Missing project.md")
        return warnings

    text = project_path.read_text()
    for section in REQUIRED_PROJECT_SECTIONS:
        if section not in text:
            warnings.append(f"project.md missing required section: {section}")

    return warnings


def find_spec_files(openspec_dir: Path) -> list[Path]:
    """Find all specs/*/spec.md files."""
    specs_dir = openspec_dir / "specs"
    if not specs_dir.is_dir():
        return []
    return sorted(specs_dir.glob("*/spec.md"))


def validate_specs_exist(openspec_dir: Path) -> list[str]:
    """Validate at least one domain spec and cross-cutting spec exist."""
    warnings = []
    spec_files = find_spec_files(openspec_dir)

    if not spec_files:
        warnings.append("No specs/*/spec.md files found")
        return warnings

    cross_cutting = openspec_dir / "specs" / "cross-cutting" / "spec.md"
    if not cross_cutting.is_file():
        warnings.append("Missing specs/cross-cutting/spec.md")

    return warnings


def validate_shall_grammar(spec_files: list[Path]) -> list[str]:
    """Check that SHALL statements use bare infinitive verbs."""
    warnings = []
    pattern = re.compile(r"SHALL\s+(\w+)", re.IGNORECASE)

    for spec_file in spec_files:
        text = spec_file.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            for match in pattern.finditer(line):
                verb = match.group(1).lower()
                if verb in BAD_SHALL_VERBS:
                    try:
                        rel_path = spec_file.relative_to(spec_file.parents[2])
                    except (ValueError, IndexError):
                        rel_path = spec_file.name
                    warnings.append(
                        f"SHALL grammar: '{match.group(0)}' in {rel_path}:{i} "
                        f"(use '{verb.rstrip('s')}' instead of '{verb}')"
                    )

    return warnings


def validate_gherkin(spec_files: list[Path]) -> list[str]:
    """Check that every Scenario block has Given, When, Then."""
    warnings = []

    for spec_file in spec_files:
        text = spec_file.read_text()
        lines = text.splitlines()
        try:
            rel_path = spec_file.relative_to(spec_file.parents[2])
        except (ValueError, IndexError):
            rel_path = spec_file.name

        # Find scenario blocks
        scenario_starts = []
        for i, line in enumerate(lines):
            if line.strip().startswith("#### Scenario:"):
                scenario_starts.append(i)

        for idx, start in enumerate(scenario_starts):
            # Block extends to next scenario or end of file
            end = scenario_starts[idx + 1] if idx + 1 < len(scenario_starts) else len(lines)
            block = "\n".join(lines[start:end])
            scenario_name = lines[start].strip().removeprefix("#### Scenario:").strip()

            has_given = "**Given**" in block
            has_when = "**When**" in block
            has_then = "**Then**" in block

            missing = []
            if not has_given:
                missing.append("Given")
            if not has_when:
                missing.append("When")
            if not has_then:
                missing.append("Then")

            if missing:
                warnings.append(
                    f"Incomplete Gherkin in {rel_path}:{start + 1} "
                    f"Scenario '{scenario_name}': missing {', '.join(missing)}"
                )

    return warnings


def validate_coverage(
    spec_files: list[Path], capabilities_path: Path
) -> list[str]:
    """Check that every CAP-F-* and CAP-NF-* appears in at least one spec."""
    warnings = []

    try:
        data = json.loads(capabilities_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        warnings.append(f"Could not read capabilities file: {e}")
        return warnings

    # Collect all CAP IDs
    cap_ids: set[str] = set()
    caps = data.get("capabilities", {})
    for cap in caps.get("functional", []):
        cap_id = cap.get("id")
        if cap_id:
            cap_ids.add(cap_id)
    for cap in caps.get("non_functional", []):
        cap_id = cap.get("id")
        if cap_id:
            cap_ids.add(cap_id)

    if not cap_ids:
        return warnings

    # Read all spec files into one text blob
    all_spec_text = ""
    for spec_file in spec_files:
        all_spec_text += spec_file.read_text() + "\n"

    # Check each CAP ID
    for cap_id in sorted(cap_ids):
        if cap_id not in all_spec_text:
            warnings.append(f"Missing coverage: {cap_id} not found in any spec file")

    return warnings


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <openspec_dir> [capabilities.json]", file=sys.stderr)
        sys.exit(1)

    openspec_dir = Path(sys.argv[1])
    capabilities_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not openspec_dir.is_dir():
        print(f"Directory not found: {openspec_dir}", file=sys.stderr)
        sys.exit(1)

    warnings: list[str] = []

    # Structure checks
    warnings.extend(validate_config(openspec_dir))
    warnings.extend(validate_project(openspec_dir))
    warnings.extend(validate_specs_exist(openspec_dir))

    # Content checks (only if spec files exist)
    spec_files = find_spec_files(openspec_dir)
    if spec_files:
        warnings.extend(validate_shall_grammar(spec_files))
        warnings.extend(validate_gherkin(spec_files))

    # Coverage check (optional)
    if capabilities_path and spec_files:
        warnings.extend(validate_coverage(spec_files, capabilities_path))

    if warnings:
        for w in warnings:
            print(f"[openspec] WARNING: {w}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
