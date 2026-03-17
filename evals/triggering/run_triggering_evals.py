#!/usr/bin/env python3
"""Phase 1 Eval: Triggering accuracy.

Tests whether the model correctly identifies which Haytham component
should handle a given user prompt.

Usage:
    python3 evals/triggering/run_triggering_evals.py
    python3 evals/triggering/run_triggering_evals.py --component validate
    python3 evals/triggering/run_triggering_evals.py --type semantic
"""

import argparse
import json
import sys
import time
from pathlib import Path

import anthropic

EVALS_DIR = Path(__file__).resolve().parent
ROOT = EVALS_DIR.parent.parent
sys.path.insert(0, str(EVALS_DIR.parent))
from shared import load_component_descriptions

RESULTS_DIR = EVALS_DIR / "results"
SCENARIOS_FILE = EVALS_DIR / "scenarios.json"
PASS_THRESHOLD = 0.85


def build_system_prompt(components: dict) -> str:
    """Build a system prompt listing all available components."""
    lines = [
        "You are a routing classifier for the Haytham plugin.",
        "Given a user prompt, determine which component should handle it.",
        "Respond with ONLY the component name, nothing else.",
        "If no component matches, respond with '_none'.",
        "",
        "Available components:",
    ]
    for name, info in sorted(components.items()):
        lines.append(f"- {name} ({info['type']}): {info['description']}")
    return "\n".join(lines)


def run_single(client: anthropic.Anthropic, system_prompt: str,
               scenario: dict, model: str) -> dict:
    """Run a single triggering scenario and return the result."""
    response = client.messages.create(
        model=model,
        max_tokens=50,
        system=system_prompt,
        messages=[{"role": "user", "content": scenario["prompt"]}],
    )
    predicted = response.content[0].text.strip().lower()
    expected = scenario["expected_component"].lower()
    passed = predicted == expected

    return {
        "id": scenario["id"],
        "prompt": scenario["prompt"],
        "expected": expected,
        "predicted": predicted,
        "passed": passed,
        "type": scenario["type"],
    }


def main():
    parser = argparse.ArgumentParser(description="Run triggering evals")
    parser.add_argument("--component", help="Only test scenarios for this component")
    parser.add_argument("--type", help="Only test scenarios of this type")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Model to use for classification")
    args = parser.parse_args()

    scenarios = json.loads(SCENARIOS_FILE.read_text())["scenarios"]

    if args.component:
        scenarios = [s for s in scenarios
                     if s["expected_component"] == args.component]
    if args.type:
        scenarios = [s for s in scenarios if s["type"] == args.type]

    if not scenarios:
        print("No matching scenarios found.")
        sys.exit(1)

    components = load_component_descriptions()
    system_prompt = build_system_prompt(components)
    client = anthropic.Anthropic()

    print(f"Running {len(scenarios)} triggering scenarios with {args.model}...")
    results = []
    for i, scenario in enumerate(scenarios):
        result = run_single(client, system_prompt, scenario, args.model)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{i+1}/{len(scenarios)}] {status} {result['id']}: "
              f"expected={result['expected']}, got={result['predicted']}")

    # Compute accuracy
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    accuracy = passed / total if total > 0 else 0

    # Per-component breakdown
    by_component = {}
    for r in results:
        comp = r["expected"]
        if comp not in by_component:
            by_component[comp] = {"total": 0, "passed": 0}
        by_component[comp]["total"] += 1
        if r["passed"]:
            by_component[comp]["passed"] += 1

    # Per-type breakdown
    by_type = {}
    for r in results:
        t = r["type"]
        if t not in by_type:
            by_type[t] = {"total": 0, "passed": 0}
        by_type[t]["total"] += 1
        if r["passed"]:
            by_type[t]["passed"] += 1

    summary = {
        "model": args.model,
        "total": total,
        "passed": passed,
        "accuracy": round(accuracy, 4),
        "pass_threshold": PASS_THRESHOLD,
        "threshold_met": accuracy >= PASS_THRESHOLD,
        "by_component": {k: {**v, "accuracy": round(v["passed"] / v["total"], 4)}
                         for k, v in sorted(by_component.items())},
        "by_type": {k: {**v, "accuracy": round(v["passed"] / v["total"], 4)}
                    for k, v in sorted(by_type.items())},
        "results": results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"triggering_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(summary, indent=2))

    print(f"\nAccuracy: {passed}/{total} = {accuracy:.1%}")
    print(f"Threshold: {PASS_THRESHOLD:.0%} {'MET' if summary['threshold_met'] else 'NOT MET'}")
    print(f"\nPer component:")
    for comp, stats in sorted(by_component.items()):
        print(f"  {comp}: {stats['passed']}/{stats['total']} = "
              f"{stats['passed']/stats['total']:.0%}")
    print(f"\nPer type:")
    for t, stats in sorted(by_type.items()):
        print(f"  {t}: {stats['passed']}/{stats['total']} = "
              f"{stats['passed']/stats['total']:.0%}")
    print(f"\nResults saved to: {out_file}")

    if not summary["threshold_met"]:
        # Print failures for debugging
        failures = [r for r in results if not r["passed"]]
        if failures:
            print(f"\nFailures ({len(failures)}):")
            for f in failures:
                print(f"  {f['id']}: expected={f['expected']}, got={f['predicted']}")
                print(f"    prompt: {f['prompt']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
