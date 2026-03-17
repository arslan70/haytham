#!/usr/bin/env python3
"""Phase 3 Eval: Consistency checks (deterministic + LLM-graded).

5 deterministic checks (free, CI-safe) + 5 LLM-graded checks (optional).
Based on review-consistency.md criteria.

Usage:
    python3 evals/e2e/consistency_checks.py --session-dir .haytham/session/
    python3 evals/e2e/consistency_checks.py --session-dir .haytham/session/ --llm
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVALS_DIR / "results"


def load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if it doesn't exist."""
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_text(path: Path) -> str | None:
    """Load a text file, returning None if it doesn't exist."""
    if not path.exists():
        return None
    return path.read_text()


# ---------------------------------------------------------------------------
# Deterministic checks (5)
# ---------------------------------------------------------------------------


def check_5_capability_traceability(session_dir: Path) -> dict:
    """Check 5: Every functional capability has a serves_scope_item that
    matches an actual IN-scope item from mvp-scope.md."""
    caps = load_json(session_dir / "phase-2-what" / "capabilities.json")
    scope_text = load_text(session_dir / "phase-2-what" / "mvp-scope.md")

    if caps is None:
        return {"check": 5, "name": "Capability Traceability",
                "result": "SKIP", "detail": "capabilities.json not found"}
    if scope_text is None:
        return {"check": 5, "name": "Capability Traceability",
                "result": "SKIP", "detail": "mvp-scope.md not found"}

    issues = []
    functional = caps.get("capabilities", {}).get("functional", [])
    for cap in functional:
        cap_id = cap.get("id", "?")
        scope_item = cap.get("serves_scope_item", "")
        if not scope_item:
            issues.append(f"{cap_id} has empty serves_scope_item")
        elif scope_item not in scope_text:
            issues.append(f"{cap_id} references '{scope_item}' not found in mvp-scope.md")

    if not issues:
        return {"check": 5, "name": "Capability Traceability",
                "result": "PASS", "detail": f"All {len(functional)} capabilities trace to scope items"}
    elif len(issues) <= 2:
        return {"check": 5, "name": "Capability Traceability",
                "result": "PARTIAL", "detail": "; ".join(issues)}
    else:
        return {"check": 5, "name": "Capability Traceability",
                "result": "FAIL", "detail": "; ".join(issues)}


def check_7_architecture_serves_capabilities(session_dir: Path) -> dict:
    """Check 7: Architecture decisions cover all capabilities via coverage_check."""
    arch = load_json(session_dir / "phase-3-how" / "architecture-decisions.json")
    caps = load_json(session_dir / "phase-2-what" / "capabilities.json")

    if arch is None:
        return {"check": 7, "name": "Architecture Serves Capabilities",
                "result": "SKIP", "detail": "architecture-decisions.json not found"}
    if caps is None:
        return {"check": 7, "name": "Architecture Serves Capabilities",
                "result": "SKIP", "detail": "capabilities.json not found"}

    # Collect all capability IDs
    all_cap_ids = set()
    for cat in ("functional", "non_functional"):
        for cap in caps.get("capabilities", {}).get(cat, []):
            all_cap_ids.add(cap.get("id", ""))

    # Collect covered capability IDs from architecture decisions
    covered = set()
    coverage_check = arch.get("coverage_check", {})
    if isinstance(coverage_check, dict):
        for cap_id_list in coverage_check.values():
            if isinstance(cap_id_list, list):
                covered.update(cap_id_list)
            elif isinstance(cap_id_list, str):
                covered.add(cap_id_list)

    # Also check decisions for capability references
    for decision in arch.get("decisions", []):
        for cap_ref in decision.get("serves_capabilities", []):
            covered.add(cap_ref)

    uncovered = all_cap_ids - covered
    if not uncovered:
        return {"check": 7, "name": "Architecture Serves Capabilities",
                "result": "PASS", "detail": f"All {len(all_cap_ids)} capabilities covered"}
    elif len(uncovered) <= 2:
        return {"check": 7, "name": "Architecture Serves Capabilities",
                "result": "PARTIAL", "detail": f"Uncovered: {', '.join(sorted(uncovered))}"}
    else:
        return {"check": 7, "name": "Architecture Serves Capabilities",
                "result": "FAIL", "detail": f"Uncovered: {', '.join(sorted(uncovered))}"}


def check_8_build_buy_consistency(session_dir: Path) -> dict:
    """Check 8: No conflicting/duplicate categories in build-buy.json."""
    bb = load_json(session_dir / "phase-3-how" / "build-buy.json")

    if bb is None:
        return {"check": 8, "name": "Build/Buy Consistency",
                "result": "SKIP", "detail": "build-buy.json not found"}

    stack = bb.get("recommended_stack", [])
    if not isinstance(stack, list):
        stack = []

    # Check for duplicate categories
    categories = {}
    issues = []
    for item in stack:
        cat = item.get("category", "")
        if cat in categories:
            prev = categories[cat]
            if item.get("recommendation") != prev.get("recommendation"):
                issues.append(
                    f"Category '{cat}' has conflicting recommendations: "
                    f"'{prev.get('recommendation')}' vs '{item.get('recommendation')}'"
                )
            else:
                issues.append(f"Category '{cat}' appears multiple times")
        categories[cat] = item

    if not issues:
        return {"check": 8, "name": "Build/Buy Consistency",
                "result": "PASS", "detail": f"Stack has {len(stack)} entries, no conflicts"}
    elif len(issues) == 1 and "appears multiple" in issues[0]:
        return {"check": 8, "name": "Build/Buy Consistency",
                "result": "PARTIAL", "detail": "; ".join(issues)}
    else:
        return {"check": 8, "name": "Build/Buy Consistency",
                "result": "FAIL", "detail": "; ".join(issues)}


def check_9_spec_coverage(session_dir: Path) -> dict:
    """Check 9: Every CAP-F-* and CAP-NF-* from capabilities.json appears
    in at least one spec file."""
    caps = load_json(session_dir / "phase-2-what" / "capabilities.json")
    spec_dir = session_dir / "phase-4-specs" / "openspec" / "specs"

    if caps is None:
        return {"check": 9, "name": "Spec Coverage",
                "result": "SKIP", "detail": "capabilities.json not found"}
    if not spec_dir.exists():
        return {"check": 9, "name": "Spec Coverage",
                "result": "SKIP", "detail": "openspec/specs/ not found"}

    # Collect all capability IDs
    all_cap_ids = set()
    for cat in ("functional", "non_functional"):
        for cap in caps.get("capabilities", {}).get(cat, []):
            cap_id = cap.get("id", "")
            if cap_id:
                all_cap_ids.add(cap_id)

    # Read all spec files and find referenced capability IDs
    spec_text = ""
    for spec_file in spec_dir.rglob("*.md"):
        spec_text += spec_file.read_text() + "\n"

    uncovered = set()
    for cap_id in all_cap_ids:
        if cap_id not in spec_text:
            uncovered.add(cap_id)

    if not uncovered:
        return {"check": 9, "name": "Spec Coverage",
                "result": "PASS", "detail": f"All {len(all_cap_ids)} capabilities referenced in specs"}
    elif len(uncovered) <= 2:
        return {"check": 9, "name": "Spec Coverage",
                "result": "PARTIAL", "detail": f"Missing from specs: {', '.join(sorted(uncovered))}"}
    else:
        return {"check": 9, "name": "Spec Coverage",
                "result": "FAIL", "detail": f"Missing from specs: {', '.join(sorted(uncovered))}"}


def check_10_cross_reference_integrity(session_dir: Path) -> dict:
    """Check 10: DEC-* IDs in project.md match architecture-decisions.json,
    and config.yaml traits match system-traits.json."""
    project_text = load_text(session_dir / "phase-4-specs" / "openspec" / "project.md")
    arch = load_json(session_dir / "phase-3-how" / "architecture-decisions.json")
    config_text = load_text(session_dir / "phase-4-specs" / "openspec" / "config.yaml")
    traits = load_json(session_dir / "phase-2-what" / "system-traits.json")

    if project_text is None:
        return {"check": 10, "name": "Cross-Reference Integrity",
                "result": "SKIP", "detail": "project.md not found"}

    issues = []

    # Check DEC-* references
    if arch is not None:
        arch_dec_ids = set()
        for dec in arch.get("decisions", []):
            dec_id = dec.get("id", "")
            if dec_id:
                arch_dec_ids.add(dec_id)

        project_dec_ids = set(re.findall(r'DEC-[A-Z]+-\d+', project_text))
        missing_in_arch = project_dec_ids - arch_dec_ids
        if missing_in_arch:
            issues.append(
                f"DEC IDs in project.md not in architecture-decisions.json: "
                f"{', '.join(sorted(missing_in_arch))}"
            )

    # Check trait consistency
    if traits is not None and config_text is not None:
        trait_keys = set(traits.get("traits", {}).keys())
        for trait in trait_keys:
            if trait not in config_text:
                issues.append(f"Trait '{trait}' from system-traits.json not in config.yaml")

    if not issues:
        return {"check": 10, "name": "Cross-Reference Integrity",
                "result": "PASS", "detail": "All cross-references resolve"}
    elif len(issues) == 1:
        return {"check": 10, "name": "Cross-Reference Integrity",
                "result": "PARTIAL", "detail": "; ".join(issues)}
    else:
        return {"check": 10, "name": "Cross-Reference Integrity",
                "result": "FAIL", "detail": "; ".join(issues)}


# ---------------------------------------------------------------------------
# LLM-graded checks (5)
# ---------------------------------------------------------------------------


def _llm_grade(client, model: str, check_num: int, name: str,
               prompt: str, anchors: dict) -> dict:
    """Run an LLM-graded consistency check."""
    system = (
        "You are grading cross-stage consistency of Haytham pipeline output.\n"
        "Respond with valid JSON only: "
        "{\"grade\": \"PASS|PARTIAL|FAIL\", \"evidence\": \"brief quote\", "
        "\"reasoning\": \"explanation\"}"
    )
    user = (
        f"## Check: {name}\n\n{prompt}\n\n"
        f"### Anchors\n"
        f"- PASS: {anchors['PASS']}\n"
        f"- PARTIAL: {anchors['PARTIAL']}\n"
        f"- FAIL: {anchors['FAIL']}\n"
    )
    response = client.messages.create(
        model=model, max_tokens=500, system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = response.content[0].text.strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        result = json.loads(match.group()) if match else {
            "grade": "ERROR", "evidence": text, "reasoning": "Parse error"
        }
    return {
        "check": check_num, "name": name,
        "result": result.get("grade", "ERROR"),
        "detail": result.get("reasoning", ""),
        "evidence": result.get("evidence", ""),
    }


def check_1_concept_anchor_preservation(session_dir: Path, client, model: str) -> dict:
    """Check 1: Concept anchor invariants appear in validation report."""
    anchor = load_json(session_dir / "phase-1-why" / "concept-anchor.json")
    report = load_text(session_dir / "phase-1-why" / "validation-report.md")
    if anchor is None or report is None:
        return {"check": 1, "name": "Concept Anchor Preservation",
                "result": "SKIP", "detail": "Required files not found"}

    prompt = (
        f"The concept anchor defines these invariants:\n"
        f"```json\n{json.dumps(anchor.get('invariants', []), indent=2)}\n```\n\n"
        f"And this identity:\n"
        f"```json\n{json.dumps(anchor.get('identity', {}), indent=2)}\n```\n\n"
        f"The validation report says:\n{report[:3000]}\n\n"
        f"Check that the invariants and identity values appear (by meaning, not exact wording) in the report."
    )
    return _llm_grade(client, model, 1, "Concept Anchor Preservation", prompt, {
        "PASS": "All invariants from concept anchor are reflected in the report",
        "PARTIAL": "Some invariants present, others not mentioned",
        "FAIL": "Report contradicts an invariant, or invariants are entirely absent",
    })


def check_2_recommendation_evidence(session_dir: Path, client, model: str) -> dict:
    """Check 2: Evidence in report supports the GO/PIVOT/NO-GO recommendation."""
    report_json = load_json(session_dir / "phase-1-why" / "validation-report.json")
    report_md = load_text(session_dir / "phase-1-why" / "validation-report.md")
    if report_json is None or report_md is None:
        return {"check": 2, "name": "Recommendation-Evidence Alignment",
                "result": "SKIP", "detail": "Required files not found"}

    rec = report_json.get("recommendation", "UNKNOWN")
    prompt = (
        f"The recommendation is: {rec}\n\n"
        f"The validation report evidence:\n{report_md[:3000]}\n\n"
        f"Does the evidence support this recommendation?"
    )
    return _llm_grade(client, model, 2, "Recommendation-Evidence Alignment", prompt, {
        "PASS": "Evidence clearly supports the stated recommendation",
        "PARTIAL": "Evidence is mixed but recommendation is plausible",
        "FAIL": "Evidence contradicts the recommendation",
    })


def check_3_analysis_to_report_continuity(session_dir: Path, client, model: str) -> dict:
    """Check 3: Idea analysis and validation report describe the same concept."""
    analysis = load_text(session_dir / "phase-1-why" / "idea-analysis.md")
    report = load_text(session_dir / "phase-1-why" / "validation-report.md")
    if analysis is None or report is None:
        return {"check": 3, "name": "Idea Analysis to Report Continuity",
                "result": "SKIP", "detail": "Required files not found"}

    prompt = (
        f"Idea analysis describes:\n{analysis[:2000]}\n\n"
        f"Validation report describes:\n{report[:2000]}\n\n"
        f"Are they describing the same concept, target user, and problem?"
    )
    return _llm_grade(client, model, 3, "Idea Analysis to Report Continuity", prompt, {
        "PASS": "Same concept, same target user, same problem",
        "PARTIAL": "Same concept but target user or problem has shifted without explanation",
        "FAIL": "Report describes a different concept than what idea analysis produced",
    })


def check_4_scope_traces_to_validation(session_dir: Path, client, model: str) -> dict:
    """Check 4: Scope items align with validation recommendation."""
    report = load_text(session_dir / "phase-1-why" / "validation-report.md")
    scope = load_text(session_dir / "phase-2-what" / "mvp-scope.md")
    if report is None or scope is None:
        return {"check": 4, "name": "Scope Traces to Validation",
                "result": "SKIP", "detail": "Required files not found"}

    prompt = (
        f"Validation report:\n{report[:2000]}\n\n"
        f"MVP scope:\n{scope[:2000]}\n\n"
        f"Do the IN-scope items align with what the validation recommended focusing on?"
    )
    return _llm_grade(client, model, 4, "Scope Traces to Validation", prompt, {
        "PASS": "Scope items align with validation findings and recommendation",
        "PARTIAL": "Mostly aligned but some scope items have no connection to validation findings",
        "FAIL": "Scope includes items the validation cautioned against, or excludes critical items",
    })


def check_6_system_traits_agreement(session_dir: Path, client, model: str) -> dict:
    """Check 6: System traits consistent with archetype from concept anchor."""
    anchor = load_json(session_dir / "phase-1-why" / "concept-anchor.json")
    traits = load_json(session_dir / "phase-2-what" / "system-traits.json")
    if anchor is None or traits is None:
        return {"check": 6, "name": "System Traits Agreement",
                "result": "SKIP", "detail": "Required files not found"}

    prompt = (
        f"Concept anchor archetype: {anchor.get('archetype', 'unknown')}\n"
        f"Invariants: {json.dumps(anchor.get('invariants', []), indent=2)}\n\n"
        f"System traits: {json.dumps(traits, indent=2)}\n\n"
        f"Are the traits consistent with the archetype and the idea's invariants?"
    )
    return _llm_grade(client, model, 6, "System Traits Agreement", prompt, {
        "PASS": "Traits align with archetype and MVP scope",
        "PARTIAL": "Some traits are generic and not clearly derived from the specific idea",
        "FAIL": "Traits contradict the archetype or describe a different kind of system",
    })


def main():
    parser = argparse.ArgumentParser(description="Run consistency checks")
    parser.add_argument("--session-dir", required=True,
                        help="Path to .haytham/session/ directory")
    parser.add_argument("--llm", action="store_true",
                        help="Also run LLM-graded checks (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--model", default="claude-opus-4-20250514",
                        help="Model for LLM checks")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.exists():
        print(f"Session directory not found: {session_dir}")
        sys.exit(1)

    results = []

    # Deterministic checks (always run)
    print("Running deterministic consistency checks...")
    deterministic_checks = [
        check_5_capability_traceability,
        check_7_architecture_serves_capabilities,
        check_8_build_buy_consistency,
        check_9_spec_coverage,
        check_10_cross_reference_integrity,
    ]
    for check_fn in deterministic_checks:
        result = check_fn(session_dir)
        results.append(result)
        print(f"  [{result['result']:7s}] Check {result['check']}: {result['name']}")
        if result["result"] in ("PARTIAL", "FAIL"):
            print(f"          {result['detail'][:120]}")

    # LLM-graded checks (optional)
    if args.llm:
        import anthropic
        client = anthropic.Anthropic()
        print("\nRunning LLM-graded consistency checks...")
        llm_checks = [
            (check_1_concept_anchor_preservation, 1),
            (check_2_recommendation_evidence, 2),
            (check_3_analysis_to_report_continuity, 3),
            (check_4_scope_traces_to_validation, 4),
            (check_6_system_traits_agreement, 6),
        ]
        for check_fn, _ in llm_checks:
            result = check_fn(session_dir, client, args.model)
            results.append(result)
            print(f"  [{result['result']:7s}] Check {result['check']}: {result['name']}")
            if result["result"] in ("PARTIAL", "FAIL"):
                print(f"          {result.get('detail', '')[:120]}")

    # Sort by check number
    results.sort(key=lambda r: r["check"])

    # Summary
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "SKIP": 0, "ERROR": 0}
    for r in results:
        counts[r["result"]] = counts.get(r["result"], 0) + 1

    print(f"\n{'='*50}")
    print(f"Consistency Check Summary")
    print(f"{'='*50}")
    print(f"PASS: {counts['PASS']}, PARTIAL: {counts['PARTIAL']}, "
          f"FAIL: {counts['FAIL']}, SKIP: {counts['SKIP']}")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "session_dir": str(session_dir),
        "llm_enabled": args.llm,
        "model": args.model if args.llm else None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totals": counts,
        "checks": results,
    }
    out_file = RESULTS_DIR / f"consistency_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved to: {out_file}")

    # Exit with error if any deterministic checks failed
    det_failures = [r for r in results if r["check"] in (5, 7, 8, 9, 10)
                    and r["result"] == "FAIL"]
    if det_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
