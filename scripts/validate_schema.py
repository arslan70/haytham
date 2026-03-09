#!/usr/bin/env python3
"""PostToolUse hook: Validate JSON files written to .haytham/session/.

Checks:
1. If the written file is in .haytham/session/ and is JSON
2. Validates required fields are present and non-empty
3. Calls validate_som.py for validation-report.json

Outputs warnings to stderr (non-blocking). Exit 0 always.
"""

import json
import os
import subprocess
import sys

# Schema definitions: file pattern -> required top-level keys
SCHEMAS = {
    "concept-anchor.json": ["archetype", "intent", "invariants", "identity"],
    "validation-report.json": [
        "recommendation",
        "executive_summary",
    ],
    "capabilities.json": ["summary", "capabilities", "traceability", "metadata"],
    "system-traits.json": ["traits", "explanations"],
    "build-buy.json": [
        "system_summary",
        "infrastructure_requirements",
        "recommended_stack",
    ],
    "architecture-decisions.json": ["decisions", "coverage_check", "summary"],
    "gate-decision.json": ["phase", "user_decision"],
}


def validate_file(file_path: str) -> list[str]:
    """Validate a JSON file against its schema. Returns warnings."""
    warnings = []

    # Only validate files in .haytham/session/
    if ".haytham/session/" not in file_path:
        return warnings

    # Only validate JSON files
    if not file_path.endswith(".json"):
        return warnings

    # Read the file
    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        warnings.append(f"Invalid JSON in {file_path}: {e}")
        return warnings
    except FileNotFoundError:
        return warnings

    # Find matching schema
    basename = os.path.basename(file_path)
    required_keys = SCHEMAS.get(basename)

    if required_keys is None:
        return warnings

    # Check required keys
    for key in required_keys:
        if key not in data:
            warnings.append(f"Missing required field '{key}' in {basename}")
        elif data[key] is None or data[key] == "" or data[key] == []:
            warnings.append(f"Empty required field '{key}' in {basename}")

    # Special validation for validation-report.json
    if basename == "validation-report.json":
        # Check recommendation value
        rec = data.get("recommendation", "")
        if rec not in ("GO", "PIVOT", "NO-GO"):
            warnings.append(
                f"Invalid recommendation '{rec}' in {basename}. "
                "Must be GO, PIVOT, or NO-GO."
            )

        # Check executive summary fields
        exec_summary = data.get("executive_summary", {})
        if isinstance(exec_summary, dict):
            required_es_fields = [
                "idea_in_one_line",
                "strongest_point",
                "recommendation_summary",
                "recommendation_reasoning",
                "competitive_snapshot",
                "closing_remark",
            ]
            for field in required_es_fields:
                if not exec_summary.get(field):
                    warnings.append(
                        f"Missing/empty executive_summary.{field} in {basename}"
                    )

        # Run SOM arithmetic validation
        script_dir = os.path.dirname(os.path.abspath(__file__))
        som_script = os.path.join(script_dir, "validate_som.py")
        if os.path.exists(som_script):
            try:
                result = subprocess.run(
                    [sys.executable, som_script, file_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.stderr.strip():
                    warnings.append(result.stderr.strip())
            except (subprocess.TimeoutExpired, OSError):
                pass

    # Special validation for capabilities.json
    if basename == "capabilities.json":
        caps = data.get("capabilities", {})
        func_caps = caps.get("functional", [])
        for cap in func_caps:
            if not cap.get("serves_scope_item"):
                cap_id = cap.get("id", "unknown")
                warnings.append(
                    f"Capability {cap_id} has no serves_scope_item traceability"
                )
            flow = cap.get("user_flow", "")
            if flow and flow not in ("Flow 1", "Flow 2", "Flow 3"):
                cap_id = cap.get("id", "unknown")
                warnings.append(f"Capability {cap_id} has invalid flow ref: {flow}")

    return warnings


def main():
    """Read tool input from stdin and validate if applicable."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # Extract the file path from the tool input
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        sys.exit(0)

    warnings = validate_file(file_path)

    if warnings:
        print("\n".join(f"[haytham] WARNING: {w}" for w in warnings), file=sys.stderr)

    # Always exit 0 (non-blocking)
    sys.exit(0)


if __name__ == "__main__":
    main()
