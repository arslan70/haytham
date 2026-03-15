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
import re
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
    "founder-corrections.json": ["corrections", "updated_at"],
    "research-directives.json": ["directives", "summary"],
}


def validate_markdown(file_path: str) -> list[str]:
    """Validate markdown files in .haytham/session/. Returns warnings."""
    warnings = []
    basename = os.path.basename(file_path)

    if basename != "idea-analysis.md":
        return warnings

    try:
        with open(file_path) as f:
            content = f.read()
    except FileNotFoundError:
        return warnings

    # Extract UVP section
    uvp_match = re.search(
        r"## 3\. Unique Value Proposition.*?\n\n(.+?)(?:\n\n|$)",
        content,
        re.DOTALL,
    )
    if not uvp_match:
        warnings.append("idea-analysis.md: UVP section (## 3) not found")
        return warnings

    uvp_text = uvp_match.group(1).strip()
    if len(uvp_text) > 140:
        warnings.append(
            f"idea-analysis.md: UVP exceeds 140 chars ({len(uvp_text)} chars)"
        )
    if " can " not in uvp_text.lower():
        warnings.append(
            "idea-analysis.md: UVP does not match '[Target] can [outcome]' format"
        )

    return warnings


def validate_file(file_path: str) -> list[str]:
    """Validate a JSON file against its schema. Returns warnings."""
    warnings = []

    # Only validate files in .haytham/session/
    if ".haytham/session/" not in file_path:
        return warnings

    # Validate markdown files
    if file_path.endswith(".md"):
        return validate_markdown(file_path)

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

    # Special validation for concept-anchor.json
    if basename == "concept-anchor.json":
        # Validate founder_profile enums
        fp = data.get("founder_profile")
        if isinstance(fp, dict):
            tl = fp.get("technical_level", "")
            if tl and tl not in ("technical", "semi-technical", "non-technical"):
                warnings.append(
                    f"Invalid founder_profile.technical_level '{tl}' in {basename}. "
                    "Must be technical, semi-technical, or non-technical."
                )
            de = fp.get("domain_expertise", "")
            if de and de not in ("high", "medium", "low"):
                warnings.append(
                    f"Invalid founder_profile.domain_expertise '{de}' in {basename}. "
                    "Must be high, medium, or low."
                )

        # Validate scope_risk on invariants
        invariants = data.get("invariants", [])
        valid_scope_risks = {"low", "medium", "high"}
        if isinstance(invariants, list):
            for i, inv in enumerate(invariants):
                if isinstance(inv, dict):
                    sr = inv.get("scope_risk")
                    if sr is not None and sr not in valid_scope_risks:
                        warnings.append(
                            f"Invalid invariants[{i}].scope_risk '{sr}' in "
                            f"{basename}. Must be low, medium, or high (or null/omitted)."
                        )

        # Validate term_flags structure
        term_flags = data.get("term_flags")
        if term_flags is not None:
            if not isinstance(term_flags, list):
                warnings.append(
                    f"term_flags must be an array in {basename}"
                )
            else:
                invariant_props = set()
                if isinstance(invariants, list):
                    for inv in invariants:
                        if isinstance(inv, dict):
                            prop = inv.get("property", "")
                            if prop:
                                invariant_props.add(prop)

                low_confidence_props = set()
                if isinstance(invariants, list):
                    for inv in invariants:
                        if isinstance(inv, dict):
                            conf = inv.get("confidence")
                            if isinstance(conf, (int, float)) and conf < 0.7:
                                prop = inv.get("property", "")
                                if prop:
                                    low_confidence_props.add(prop)

                flagged_invariant_refs = set()
                for i, flag in enumerate(term_flags):
                    if not isinstance(flag, dict):
                        warnings.append(
                            f"term_flags[{i}] is not an object in {basename}"
                        )
                        continue
                    for req_field in ("term", "chosen_interpretation",
                                      "alternatives", "impact"):
                        val = flag.get(req_field)
                        if not val:
                            warnings.append(
                                f"Missing/empty term_flags[{i}].{req_field} "
                                f"in {basename}"
                            )
                    alts = flag.get("alternatives")
                    if alts is not None and (
                        not isinstance(alts, list) or len(alts) == 0
                    ):
                        warnings.append(
                            f"term_flags[{i}].alternatives must be a "
                            f"non-empty array in {basename}"
                        )
                    inv_refs = flag.get("invariant_refs")
                    if inv_refs is not None:
                        if not isinstance(inv_refs, list):
                            warnings.append(
                                f"term_flags[{i}].invariant_refs must be "
                                f"an array in {basename}"
                            )
                        else:
                            for ref in inv_refs:
                                flagged_invariant_refs.add(ref)
                                if ref not in invariant_props:
                                    warnings.append(
                                        f"term_flags[{i}].invariant_refs "
                                        f"references '{ref}' which is not in "
                                        f"invariants in {basename}"
                                    )

                # Consistency: warn if low-confidence invariants lack term flags
                unflagged_low_conf = low_confidence_props - flagged_invariant_refs
                for prop in sorted(unflagged_low_conf):
                    warnings.append(
                        f"Invariant '{prop}' has confidence < 0.7 but is not "
                        f"referenced by any term_flags entry in {basename}"
                    )

        # Validate strategic_signals enums
        ss = data.get("strategic_signals")
        if isinstance(ss, dict):
            valid_enums = {
                "business_model": {
                    "open-source", "saas", "freemium", "marketplace",
                    "agency", "unknown",
                },
                "success_metric": {
                    "revenue", "community_adoption", "usage",
                    "enterprise_contracts", "unknown",
                },
                "distribution": {
                    "standalone", "plugin_or_extension", "hosted",
                    "marketplace_listing", "unknown",
                },
            }
            for field, allowed in valid_enums.items():
                val = ss.get(field, "")
                if val and val not in allowed:
                    warnings.append(
                        f"Invalid strategic_signals.{field} '{val}' in {basename}. "
                        f"Must be one of: {sorted(allowed)}"
                    )

    # Special validation for founder-corrections.json
    if basename == "founder-corrections.json":
        valid_dimensions = {
            "problem", "competition", "market_size",
            "positioning", "business_model", "other",
        }
        corrections = data.get("corrections", [])
        if isinstance(corrections, list):
            for i, entry in enumerate(corrections):
                if not isinstance(entry, dict):
                    warnings.append(
                        f"corrections[{i}] is not an object in {basename}"
                    )
                    continue
                dim = entry.get("dimension", "")
                if dim and dim not in valid_dimensions:
                    warnings.append(
                        f"Invalid corrections[{i}].dimension '{dim}' in {basename}. "
                        f"Must be one of: {sorted(valid_dimensions)}"
                    )
                if not entry.get("correction"):
                    warnings.append(
                        f"Missing/empty corrections[{i}].correction in {basename}"
                    )

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

    # Special validation for system-traits.json
    if basename == "system-traits.json":
        valid_trait_names = {
            "interface", "auth", "deployment", "data_layer",
            "realtime", "communication", "payments", "scheduling",
        }
        explanations = data.get("explanations", {})
        if isinstance(explanations, dict):
            for key, value in explanations.items():
                if key not in valid_trait_names:
                    warnings.append(
                        f"Unknown trait '{key}' in explanations in {basename}. "
                        f"Must be one of: {sorted(valid_trait_names)}"
                    )
                if not isinstance(value, str):
                    warnings.append(
                        f"explanations.{key} is {type(value).__name__}, "
                        f"not a string in {basename}"
                    )

    # Special validation for capabilities.json
    if basename == "capabilities.json":
        valid_flows = {"Flow 1", "Flow 2", "Flow 3"}
        caps = data.get("capabilities", {})
        func_caps = caps.get("functional", [])
        for cap in func_caps:
            cap_id = cap.get("id", "unknown")
            if not cap.get("serves_scope_item"):
                warnings.append(
                    f"Capability {cap_id} has no serves_scope_item traceability"
                )
            flow = cap.get("user_flow", "")
            if flow:
                parts = [p.strip() for p in flow.split("|")]
                for part in parts:
                    if part not in valid_flows:
                        warnings.append(
                            f"Capability {cap_id} has invalid flow ref: {part}"
                        )
            # Mega-capability detection: serves_scope_item should be a single item
            scope_item = cap.get("serves_scope_item", "")
            if scope_item and (" | " in scope_item or ", " in scope_item):
                warnings.append(
                    f"Capability {cap_id} serves multiple scope items: "
                    f"'{scope_item}'. Split into one capability per scope item."
                )

        # Capability count vs scope items covered
        traceability = data.get("traceability", {})
        scope_items = traceability.get("scope_items_covered", [])
        if scope_items and func_caps:
            diff = abs(len(func_caps) - len(scope_items))
            if diff > 2:
                warnings.append(
                    f"Capability count ({len(func_caps)}) differs from "
                    f"scope items covered ({len(scope_items)}) by {diff} "
                    f"in {basename}. Expected roughly 1:1 mapping."
                )

    # Special validation for architecture-decisions.json
    if basename == "architecture-decisions.json":
        # Check uncovered capabilities
        coverage = data.get("coverage_check", {})
        uncovered = coverage.get("uncovered", [])
        if uncovered:
            warnings.append(
                f"Architecture has uncovered capabilities: "
                f"{uncovered} in {basename}"
            )

        # Validate decision ID format
        valid_dec_categories = {
            "AUTH", "DB", "DEPLOY", "NOTIFY", "REALTIME",
            "INTEGRITY", "ORCHESTRATION", "STACK",
        }
        for decision in data.get("decisions", []):
            dec_id = decision.get("id", "")
            match = re.match(r"^DEC-([A-Z]+)-(\d{3})$", dec_id)
            if not match:
                warnings.append(
                    f"Invalid decision ID format '{dec_id}' in {basename}. "
                    f"Expected DEC-CATEGORY-NNN."
                )
            elif match.group(1) not in valid_dec_categories:
                warnings.append(
                    f"Custom decision category '{match.group(1)}' in "
                    f"{dec_id} in {basename} (not in default set: "
                    f"{sorted(valid_dec_categories)})"
                )

        # Cross-file: verify claimed coverage matches actual capabilities
        session_dir = os.path.dirname(os.path.dirname(file_path))
        caps_path = os.path.join(session_dir, "phase-2-what", "capabilities.json")
        if os.path.exists(caps_path):
            try:
                with open(caps_path) as cf:
                    caps_data = json.load(cf)
                all_cap_ids = set()
                for cap in caps_data.get("capabilities", {}).get("functional", []):
                    all_cap_ids.add(cap.get("id", ""))
                for cap in caps_data.get("capabilities", {}).get(
                    "non_functional", []
                ):
                    all_cap_ids.add(cap.get("id", ""))
                covered = set(coverage.get("functional_covered", []))
                covered.update(coverage.get("non_functional_covered", []))
                actually_uncovered = all_cap_ids - covered
                if actually_uncovered:
                    warnings.append(
                        f"Architecture claims full coverage but these "
                        f"capabilities from capabilities.json are not in "
                        f"coverage_check: {sorted(actually_uncovered)}"
                    )
            except (json.JSONDecodeError, KeyError):
                pass

    # Special validation for build-buy.json
    if basename == "build-buy.json":
        # Validate developer_model when platform_opportunity is assessed
        platform = data.get("platform_opportunity")
        if isinstance(platform, dict) and platform.get("assessed"):
            dev_model = platform.get("developer_model")
            if not isinstance(dev_model, dict):
                warnings.append(
                    f"platform_opportunity.assessed is true but "
                    f"developer_model is missing in {basename}. "
                    f"The architect should research the platform's "
                    f"developer docs before making stack decisions."
                )
            else:
                for field in ("source", "plugin_format",
                              "runtime_provides", "distribution_mechanism"):
                    val = dev_model.get(field)
                    if not val or val == []:
                        warnings.append(
                            f"Empty/missing developer_model.{field} "
                            f"in {basename}"
                        )

        valid_categories = {
            "database", "auth", "payments", "storage", "email", "hosting",
            "search", "realtime", "video", "scheduling", "llm_api", "compute",
        }
        valid_recommendations = {"BUILD", "BUY", "HYBRID", "PLATFORM"}
        infra = data.get("infrastructure_requirements", [])
        if isinstance(infra, list):
            for i, item in enumerate(infra):
                if isinstance(item, dict):
                    cat = item.get("category", "")
                    if cat and cat not in valid_categories:
                        warnings.append(
                            f"Custom infrastructure_requirements[{i}].category "
                            f"'{cat}' in {basename} (not in default set: "
                            f"{sorted(valid_categories)})"
                        )
        stack = data.get("recommended_stack", [])
        if isinstance(stack, list):
            for i, item in enumerate(stack):
                if isinstance(item, dict):
                    rec = item.get("recommendation", "")
                    if rec and rec not in valid_recommendations:
                        warnings.append(
                            f"Invalid recommended_stack[{i}].recommendation "
                            f"'{rec}' in {basename}. "
                            f"Must be one of: {sorted(valid_recommendations)}"
                        )

    # Special validation for research-directives.json
    if basename == "research-directives.json":
        valid_classifications = {
            "llm_dependent", "algorithm_dependent",
            "integration_dependent", "domain_dependent", "standard",
        }
        directives = data.get("directives", [])
        research_count = 0
        if isinstance(directives, list):
            for i, directive in enumerate(directives):
                if not isinstance(directive, dict):
                    warnings.append(
                        f"directives[{i}] is not an object in {basename}"
                    )
                    continue

                cap_id = directive.get("capability_id", "")
                classifications = directive.get("classifications", [])
                research_req = directive.get("research_required", False)
                questions = directive.get("questions", [])

                # Validate classifications
                if not isinstance(classifications, list) or not classifications:
                    warnings.append(
                        f"directives[{i}] ({cap_id}): classifications must be "
                        f"a non-empty array in {basename}"
                    )
                else:
                    for cls in classifications:
                        if cls not in valid_classifications:
                            warnings.append(
                                f"directives[{i}] ({cap_id}): invalid "
                                f"classification '{cls}' in {basename}. "
                                f"Must be one of: "
                                f"{sorted(valid_classifications)}"
                            )
                    # standard is exclusive
                    if "standard" in classifications and len(classifications) > 1:
                        warnings.append(
                            f"directives[{i}] ({cap_id}): 'standard' "
                            f"classification must be exclusive (cannot mix "
                            f"with other classifications) in {basename}"
                        )

                # research_required consistency
                if research_req:
                    research_count += 1
                    if "standard" in (classifications if isinstance(classifications, list) else []):
                        warnings.append(
                            f"directives[{i}] ({cap_id}): research_required "
                            f"is true but classifications includes 'standard' "
                            f"in {basename}"
                        )
                    if not isinstance(questions, list) or not questions:
                        warnings.append(
                            f"directives[{i}] ({cap_id}): research_required "
                            f"is true but questions is empty in {basename}"
                        )
                else:
                    if not isinstance(classifications, list) or classifications != ["standard"]:
                        warnings.append(
                            f"directives[{i}] ({cap_id}): research_required "
                            f"is false but classifications is not "
                            f"['standard'] in {basename}"
                        )

        # Summary validation
        summary = data.get("summary", {})
        if isinstance(summary, dict):
            total = summary.get("total", 0)
            requiring = summary.get("requiring_research", 0)
            if total != len(directives):
                warnings.append(
                    f"summary.total ({total}) does not match "
                    f"len(directives) ({len(directives)}) in {basename}"
                )
            if requiring != research_count:
                warnings.append(
                    f"summary.requiring_research ({requiring}) does not "
                    f"match actual count ({research_count}) in {basename}"
                )

        # Cross-file: verify capability IDs exist in capabilities.json
        session_dir = os.path.dirname(os.path.dirname(file_path))
        caps_path = os.path.join(session_dir, "phase-2-what", "capabilities.json")
        if os.path.exists(caps_path):
            try:
                with open(caps_path) as cf:
                    caps_data = json.load(cf)
                func_cap_ids = set()
                for cap in caps_data.get("capabilities", {}).get(
                    "functional", []
                ):
                    func_cap_ids.add(cap.get("id", ""))

                directive_cap_ids = set()
                for directive in directives:
                    if isinstance(directive, dict):
                        cap_id = directive.get("capability_id", "")
                        if cap_id:
                            directive_cap_ids.add(cap_id)
                            if cap_id not in func_cap_ids:
                                warnings.append(
                                    f"Directive references '{cap_id}' which "
                                    f"does not exist in capabilities.json"
                                )

                # Every CAP-F-* should have a directive
                missing = func_cap_ids - directive_cap_ids
                if missing:
                    warnings.append(
                        f"Capabilities missing from directives: "
                        f"{sorted(missing)}"
                    )
            except (json.JSONDecodeError, KeyError):
                pass

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
