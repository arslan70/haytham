#!/usr/bin/env python3
"""Phase 2 Eval: Quality grading via LLM rubrics.

Grades Haytham session output against codified rubric criteria using
Claude as a grader. Each criterion produces PASS/PARTIAL/FAIL with evidence.

Usage:
    python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/
    python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --rubric idea-analysis
    python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --compare-baseline baselines/baseline_20260317.json
    python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --update-baseline
"""

import argparse
import json
import sys
import time
from pathlib import Path

import anthropic

EVALS_DIR = Path(__file__).resolve().parent
RUBRICS_DIR = EVALS_DIR / "grading_rubrics"
RESULTS_DIR = EVALS_DIR / "results"
BASELINES_DIR = EVALS_DIR.parent / "baselines"

GRADE_VALUES = {"PASS": 2, "PARTIAL": 1, "FAIL": 0}


def load_rubric(name: str) -> dict:
    """Load a rubric JSON file by name (without extension)."""
    path = RUBRICS_DIR / f"{name}.json"
    return json.loads(path.read_text())


def load_session_file(session_dir: Path, relative_path: str) -> str | None:
    """Load a session file, returning None if it doesn't exist."""
    path = session_dir / relative_path
    if not path.exists():
        return None
    return path.read_text()


def load_session_files_for_rubric(session_dir: Path, rubric: dict) -> dict:
    """Load all session files referenced by a rubric."""
    files = {}
    for rel_path in rubric["session_files"]:
        full_path = session_dir / rel_path
        if full_path.is_dir():
            # Load all files in directory (for openspec/specs/)
            for child in sorted(full_path.rglob("*")):
                if child.is_file():
                    rel = str(child.relative_to(session_dir))
                    files[rel] = child.read_text()
        elif full_path.exists():
            files[rel_path] = full_path.read_text()
    return files


def grade_criterion(client: anthropic.Anthropic, criterion: dict,
                    session_files: dict, model: str) -> dict:
    """Grade a single criterion against session files."""
    # Build context from available files
    file_context = []
    for path, content in session_files.items():
        file_context.append(f"--- {path} ---\n{content}\n")

    if not file_context:
        return {
            "id": criterion["id"],
            "name": criterion["name"],
            "grade": "SKIP",
            "evidence": "No session files available for this criterion",
            "reasoning": "",
        }

    system_prompt = (
        "You are a strict grader evaluating Haytham pipeline output quality.\n"
        "Grade the following criterion using ONLY the anchors provided.\n"
        "You MUST respond with valid JSON and nothing else.\n"
        "Format: {\"grade\": \"PASS|PARTIAL|FAIL\", \"evidence\": \"direct quote\", "
        "\"reasoning\": \"why this grade\"}"
    )

    user_prompt = (
        f"## Criterion: {criterion['name']}\n\n"
        f"{criterion['grading_prompt']}\n\n"
        f"### Grading Anchors\n"
        f"- PASS: {criterion['anchors']['PASS']}\n"
        f"- PARTIAL: {criterion['anchors']['PARTIAL']}\n"
        f"- FAIL: {criterion['anchors']['FAIL']}\n\n"
        f"### Session Output to Grade\n\n"
        + "\n".join(file_context)
    )

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = response.content[0].text.strip()
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = {
                "grade": "ERROR",
                "evidence": "Failed to parse grader response",
                "reasoning": response_text,
            }

    return {
        "id": criterion["id"],
        "name": criterion["name"],
        "grade": result.get("grade", "ERROR"),
        "evidence": result.get("evidence", ""),
        "reasoning": result.get("reasoning", ""),
    }


def compare_with_baseline(results: dict, baseline_path: Path) -> dict:
    """Compare current results with a baseline, returning regressions."""
    baseline = json.loads(baseline_path.read_text())
    baseline_grades = {}
    for rubric_result in baseline.get("rubric_results", []):
        for criterion in rubric_result.get("criteria_results", []):
            baseline_grades[criterion["id"]] = criterion["grade"]

    regressions = []
    improvements = []
    for rubric_result in results.get("rubric_results", []):
        for criterion in rubric_result.get("criteria_results", []):
            cid = criterion["id"]
            current = criterion["grade"]
            prev = baseline_grades.get(cid)
            if prev and current in GRADE_VALUES and prev in GRADE_VALUES:
                if GRADE_VALUES[current] < GRADE_VALUES[prev]:
                    regressions.append({
                        "id": cid,
                        "name": criterion["name"],
                        "was": prev,
                        "now": current,
                    })
                elif GRADE_VALUES[current] > GRADE_VALUES[prev]:
                    improvements.append({
                        "id": cid,
                        "name": criterion["name"],
                        "was": prev,
                        "now": current,
                    })

    return {"regressions": regressions, "improvements": improvements}


def main():
    parser = argparse.ArgumentParser(description="Run quality evals")
    parser.add_argument("--session-dir", required=True,
                        help="Path to .haytham/session/ directory")
    parser.add_argument("--rubric", help="Only run a specific rubric (by name)")
    parser.add_argument("--model", default="claude-opus-4-20250514",
                        help="Model to use for grading")
    parser.add_argument("--compare-baseline",
                        help="Path to baseline JSON for regression comparison")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Save results as new baseline")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.exists():
        print(f"Session directory not found: {session_dir}")
        sys.exit(1)

    # Load rubrics
    rubric_names = [args.rubric] if args.rubric else [
        p.stem for p in sorted(RUBRICS_DIR.glob("*.json"))
    ]

    client = anthropic.Anthropic()
    all_results = []
    total_counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "SKIP": 0, "ERROR": 0}

    for rubric_name in rubric_names:
        rubric = load_rubric(rubric_name)
        session_files = load_session_files_for_rubric(session_dir, rubric)

        if not session_files:
            print(f"\n[SKIP] {rubric['name']} - no session files found")
            skipped = [{
                "id": c["id"], "name": c["name"], "grade": "SKIP",
                "evidence": "Session files not found", "reasoning": "",
            } for c in rubric["criteria"]]
            all_results.append({
                "rubric": rubric_name,
                "rubric_name": rubric["name"],
                "criteria_results": skipped,
            })
            total_counts["SKIP"] += len(skipped)
            continue

        print(f"\n[GRADING] {rubric['name']} ({len(rubric['criteria'])} criteria)")
        criteria_results = []
        for criterion in rubric["criteria"]:
            result = grade_criterion(client, criterion, session_files, args.model)
            criteria_results.append(result)
            grade = result["grade"]
            total_counts[grade] = total_counts.get(grade, 0) + 1
            print(f"  {grade:7s} {result['id']}: {result['name']}")
            if grade in ("PARTIAL", "FAIL"):
                print(f"          Evidence: {result['evidence'][:100]}")

        all_results.append({
            "rubric": rubric_name,
            "rubric_name": rubric["name"],
            "criteria_results": criteria_results,
        })

    summary = {
        "model": args.model,
        "session_dir": str(session_dir),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totals": total_counts,
        "rubric_results": all_results,
    }

    # Print summary
    graded = total_counts["PASS"] + total_counts["PARTIAL"] + total_counts["FAIL"]
    print(f"\n{'='*50}")
    print(f"Quality Eval Summary")
    print(f"{'='*50}")
    print(f"PASS: {total_counts['PASS']}, PARTIAL: {total_counts['PARTIAL']}, "
          f"FAIL: {total_counts['FAIL']}, SKIP: {total_counts['SKIP']}")
    if graded > 0:
        score = (total_counts["PASS"] * 2 + total_counts["PARTIAL"]) / (graded * 2)
        print(f"Quality score: {score:.0%} ({total_counts['PASS']}/{graded} full pass)")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"quality_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(summary, indent=2))
    print(f"\nResults saved to: {out_file}")

    # Baseline comparison
    if args.compare_baseline:
        baseline_path = Path(args.compare_baseline)
        if baseline_path.exists():
            comparison = compare_with_baseline(summary, baseline_path)
            if comparison["regressions"]:
                print(f"\nREGRESSIONS ({len(comparison['regressions'])}):")
                for r in comparison["regressions"]:
                    print(f"  {r['id']} ({r['name']}): {r['was']} -> {r['now']}")
            if comparison["improvements"]:
                print(f"\nIMPROVEMENTS ({len(comparison['improvements'])}):")
                for i in comparison["improvements"]:
                    print(f"  {i['id']} ({i['name']}): {i['was']} -> {i['now']}")
            if not comparison["regressions"] and not comparison["improvements"]:
                print("\nNo changes from baseline.")

    # Update baseline
    if args.update_baseline:
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        baseline_file = BASELINES_DIR / f"baseline_{time.strftime('%Y%m%d_%H%M%S')}.json"
        baseline_file.write_text(json.dumps(summary, indent=2))
        print(f"Baseline saved to: {baseline_file}")


if __name__ == "__main__":
    main()
