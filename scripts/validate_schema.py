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


def _count_section_words(content: str, header_pattern: str, next_header: str = r"^#{1,4} ") -> int:
    """Count words in a markdown section between header_pattern and next heading."""
    match = re.search(header_pattern, content, re.MULTILINE)
    if not match:
        return 0
    start = match.end()
    rest = content[start:]
    next_match = re.search(next_header, rest, re.MULTILINE)
    section_text = rest[:next_match.start()] if next_match else rest
    return len(section_text.split())


# Banned judgment words for research-brief.md
BANNED_BRIEF_WORDS = [
    "strong", "weak", "promising", "concerning", "impressive",
    "worrying", "significant", "notable", "better than", "worse than",
    "leading", "lagging", "large market", "tough competition",
    "clear opportunity",
]


def validate_markdown(file_path: str) -> list[str]:
    """Validate markdown files in .haytham/session/. Returns warnings."""
    warnings = []
    basename = os.path.basename(file_path)

    try:
        with open(file_path) as f:
            content = f.read()
    except FileNotFoundError:
        return warnings

    # --- idea-analysis.md ---
    if basename == "idea-analysis.md":
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

    # --- validation-report.md (E1, E2, E3) ---
    if basename == "validation-report.md":
        # E1: Check all 11 sections present
        required_sections = [
            (r"#+\s*1\.\s*The Opportunity", "1. The Opportunity"),
            (r"#+\s*2\.\s*Competitive Landscape", "2. Competitive Landscape"),
            (r"#+\s*3\.\s*Claims\s*&?\s*Evidence", "3. Claims & Evidence"),
            (r"#+\s*4\.\s*Risk Profile", "4. Risk Profile"),
            (r"#+\s*5\.\s*Financial Feasibility", "5. Financial Feasibility"),
            (r"#+\s*6\.\s*Our Recommendation", "6. Our Recommendation"),
            (r"#+\s*7\.\s*Validate Before You Build", "7. Validate Before You Build"),
            (r"#+\s*8\.\s*Next Steps", "8. Next Steps"),
            (r"#+\s*9\.\s*Positioning Analysis", "9. Positioning Analysis"),
            (r"#+\s*10\.\s*Strategic Options", "10. Strategic Options"),
            (r"#+\s*11\.\s*Assumptions\s*&?\s*Evidence", "11. Assumptions & Evidence"),
        ]
        for pattern, name in required_sections:
            if not re.search(pattern, content):
                warnings.append(
                    f"validation-report.md: Missing section '{name}'"
                )

        # E2: Composite score consistency (check markdown side; JSON checked separately)
        score_match = re.search(
            r"\*\*Composite Score:\*\*\s*(\d+\.?\d*)\s*/\s*5\.0",
            content,
        )
        if not score_match:
            warnings.append(
                "validation-report.md: 'Composite Score: X.X/5.0' not found"
            )
        else:
            # Store for cross-file check (caller must handle)
            pass

        # E3: Dealbreaker check presence
        if "Dealbreaker" not in content and "dealbreaker" not in content:
            warnings.append(
                "validation-report.md: Dealbreaker check not found in Risk Profile"
            )

    # --- research-brief.md (E7, E11) ---
    if basename == "research-brief.md":
        content_lower = content.lower()
        for word in BANNED_BRIEF_WORDS:
            if word.lower() in content_lower:
                # Find line number for context
                for i, line in enumerate(content.splitlines(), 1):
                    if word.lower() in line.lower():
                        warnings.append(
                            f"research-brief.md: Banned judgment word '{word}' "
                            f"found on line {i}"
                        )
                        break

        # E11: Evidence tag preservation check
        brief_dir = os.path.dirname(file_path)
        upstream_tags = set()
        for upstream_name in ("market-research.md", "competitor-research.md"):
            upstream_path = os.path.join(brief_dir, upstream_name)
            if os.path.exists(upstream_path):
                try:
                    with open(upstream_path) as uf:
                        upstream_content = uf.read()
                    # Extract all evidence tags: [Verified: X], [Estimate: X], [Assumption]
                    tags = re.findall(
                        r"\[(Verified|Estimate|Assumption)(?::\s*([^\]]*))?\]",
                        upstream_content,
                    )
                    for tag_type, tag_source in tags:
                        if tag_source:
                            upstream_tags.add((tag_type, tag_source.strip()))
                except OSError:
                    pass

        if upstream_tags:
            brief_tags = set()
            tags_in_brief = re.findall(
                r"\[(Verified|Estimate|Assumption)(?::\s*([^\]]*))?\]",
                content,
            )
            for tag_type, tag_source in tags_in_brief:
                if tag_source:
                    brief_tags.add((tag_type, tag_source.strip()))

            # Check if brief introduces tags not found upstream
            novel_tags = brief_tags - upstream_tags
            for tag_type, tag_source in novel_tags:
                warnings.append(
                    f"research-brief.md: Evidence tag [{tag_type}: {tag_source}] "
                    f"not found in upstream research files (possible tag mismatch)"
                )

    # --- market-research.md (E8, E9) ---
    if basename == "market-research.md":
        # E8: Trend count and counter-trend check
        trend_matches = re.findall(
            r"\*\*Trend\s+\d+", content
        )
        if trend_matches and len(trend_matches) != 3:
            warnings.append(
                f"market-research.md: Found {len(trend_matches)} trends; "
                f"requires exactly 3"
            )
        if trend_matches and "counter-trend" not in content.lower() and "counter" not in content.lower():
            warnings.append(
                "market-research.md: No counter-trend found; "
                "requires at least 1"
            )

        # E9: Section word budget checks
        section_budgets = {
            r"#+\s*1\.\s*Market Context": ("1. Market Context", 80),
            r"#+\s*2\.\s*Jobs-to-be-Done": ("2. JTBD", 150),
            r"#+\s*3\.\s*Market Size": ("3. Market Size", 50),
            r"#+\s*4\.\s*Market Trends": ("4. Market Trends", 140),
            r"#+\s*5\.\s*Market Risks": ("5. Market Risks", 100),
        }
        for pattern, (name, budget) in section_budgets.items():
            words = _count_section_words(content, pattern)
            if words > 0 and words > budget * 1.25:
                warnings.append(
                    f"market-research.md: Section '{name}' has {words} words "
                    f"(budget: {budget}, 25% tolerance: {int(budget * 1.25)})"
                )

    # --- competitor-research.md (E9) ---
    if basename == "competitor-research.md":
        section_budgets = {
            r"#+\s*1\.\s*Competitor Identification": ("1. Competitor ID", 300),
            r"#+\s*2\.\s*User Sentiment": ("2. Sentiment", 120),
            r"#+\s*3\.\s*Competitive Positioning": ("3. Positioning", 70),
            r"#+\s*4\.\s*Switching Analysis": ("4. Switching", 50),
            r"#+\s*5\.\s*Competitive Gaps": ("5. Gaps & Challenges", 160),
            r"#+\s*6\.\s*Confirmation Bias": ("6. Bias Check", 30),
            r"#+\s*7\.\s*Competitive Stance": ("7. Stance", 20),
        }
        for pattern, (name, budget) in section_budgets.items():
            words = _count_section_words(content, pattern)
            if words > 0 and words > budget * 1.25:
                warnings.append(
                    f"competitor-research.md: Section '{name}' has {words} words "
                    f"(budget: {budget}, 25% tolerance: {int(budget * 1.25)})"
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

        # E4: Validate required invariants (access_model, interaction_model, session_medium)
        invariants = data.get("invariants", [])
        if isinstance(invariants, list):
            invariant_properties = {
                inv.get("property", "") for inv in invariants
                if isinstance(inv, dict)
            }
            for required_prop in ("access_model", "interaction_model", "session_medium"):
                if required_prop not in invariant_properties:
                    warnings.append(
                        f"Missing required invariant '{required_prop}' in {basename}"
                    )

            # E5: Validate confidence score range [0.0, 1.0]
            for i, inv in enumerate(invariants):
                if isinstance(inv, dict):
                    conf = inv.get("confidence")
                    if isinstance(conf, (int, float)):
                        if conf < 0.0 or conf > 1.0:
                            warnings.append(
                                f"Invalid invariants[{i}].confidence {conf} in "
                                f"{basename}. Must be in [0.0, 1.0]."
                            )

        # Validate scope_risk on invariants
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
                # E6: Term flags cap (max 3)
                if len(term_flags) > 3:
                    warnings.append(
                        f"term_flags has {len(term_flags)} entries in {basename}. "
                        f"Hard cap is 3."
                    )

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
                "growth_model": {
                    "viral", "content", "community", "sales",
                    "organic_oss", "ecosystem", "unknown",
                },
            }
            for field, allowed in valid_enums.items():
                val = ss.get(field, "")
                if val and val not in allowed:
                    warnings.append(
                        f"Invalid strategic_signals.{field} '{val}' in {basename}. "
                        f"Must be one of: {sorted(allowed)}"
                    )

        # Validate founder_intent (optional but structured when present)
        fi = data.get("founder_intent")
        if fi is not None:
            if not isinstance(fi, dict):
                warnings.append(
                    f"founder_intent must be an object in {basename}"
                )
            else:
                valid_motivations = {
                    "learning", "revenue", "community", "credibility",
                    "solving_own_problem", "unknown",
                }
                motivation = fi.get("motivation", "")
                if motivation and motivation not in valid_motivations:
                    warnings.append(
                        f"Invalid founder_intent.motivation '{motivation}' "
                        f"in {basename}. "
                        f"Must be one of: {sorted(valid_motivations)}"
                    )
                constraints = fi.get("constraints")
                if isinstance(constraints, dict):
                    valid_horizons = {"weeks", "months", "quarters"}
                    th = constraints.get("time_horizon", "")
                    if th and th not in valid_horizons:
                        warnings.append(
                            f"Invalid founder_intent.constraints.time_horizon "
                            f"'{th}' in {basename}. "
                            f"Must be one of: {sorted(valid_horizons)}"
                        )
                    valid_teams = {"solo", "small_team", "funded_team"}
                    team = constraints.get("team", "")
                    if team and team not in valid_teams:
                        warnings.append(
                            f"Invalid founder_intent.constraints.team "
                            f"'{team}' in {basename}. "
                            f"Must be one of: {sorted(valid_teams)}"
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
        # E2: Cross-file composite score consistency
        report_md_path = os.path.join(os.path.dirname(file_path), "validation-report.md")
        if os.path.exists(report_md_path):
            try:
                with open(report_md_path) as mf:
                    md_content = mf.read()
                score_match = re.search(
                    r"\*\*Composite Score:\*\*\s*(\d+\.?\d*)\s*/\s*5\.0",
                    md_content,
                )
                json_score = data.get("composite_score")
                if score_match and json_score is not None:
                    md_score = float(score_match.group(1))
                    if abs(md_score - float(json_score)) > 0.1:
                        warnings.append(
                            f"Composite score mismatch: markdown has {md_score}, "
                            f"JSON has {json_score} in {basename}"
                        )
            except (OSError, ValueError):
                pass
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

        # Validate recommended_path (optional)
        valid_paths = {
            "build_mvp", "validate_first", "build_community",
            "content_first", "experiment", "pivot",
        }
        path = data.get("recommended_path", "")
        if path and path not in valid_paths:
            warnings.append(
                f"Invalid recommended_path '{path}' in {basename}. "
                f"Must be one of: {sorted(valid_paths)}"
            )

        # Validate positioning (optional)
        positioning = data.get("positioning")
        if isinstance(positioning, dict):
            valid_defensibility = {"weak", "moderate", "strong"}
            d = positioning.get("defensibility", "")
            if d and d not in valid_defensibility:
                warnings.append(
                    f"Invalid positioning.defensibility '{d}' in {basename}. "
                    f"Must be one of: {sorted(valid_defensibility)}"
                )
            valid_fmf = {"strong", "moderate", "weak"}
            fmf = positioning.get("founder_market_fit", "")
            if fmf and fmf not in valid_fmf:
                warnings.append(
                    f"Invalid positioning.founder_market_fit '{fmf}' "
                    f"in {basename}. "
                    f"Must be one of: {sorted(valid_fmf)}"
                )

        # Validate assumptions array (optional)
        assumptions = data.get("assumptions")
        if assumptions is not None:
            if not isinstance(assumptions, list):
                warnings.append(
                    f"assumptions must be an array in {basename}"
                )
            else:
                valid_evidence = {"supported", "belief", "untested"}
                for i, a in enumerate(assumptions):
                    if not isinstance(a, dict):
                        warnings.append(
                            f"assumptions[{i}] is not an object "
                            f"in {basename}"
                        )
                        continue
                    if not a.get("claim"):
                        warnings.append(
                            f"Missing/empty assumptions[{i}].claim "
                            f"in {basename}"
                        )
                    el = a.get("evidence_level", "")
                    if el and el not in valid_evidence:
                        warnings.append(
                            f"Invalid assumptions[{i}].evidence_level "
                            f"'{el}' in {basename}. "
                            f"Must be one of: {sorted(valid_evidence)}"
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
            if len(func_caps) < len(scope_items):
                warnings.append(
                    f"Fewer capabilities ({len(func_caps)}) than scope items "
                    f"({len(scope_items)}) in {basename}. Every IN SCOPE item "
                    f"needs at least one capability."
                )
            elif len(func_caps) > len(scope_items) * 4:
                warnings.append(
                    f"Capability count ({len(func_caps)}) is more than 4x scope "
                    f"items ({len(scope_items)}) in {basename}. Check for scope "
                    f"creep or over-decomposition."
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
