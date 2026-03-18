#!/usr/bin/env python3
"""Phase 3 Eval: End-to-end evaluation runner.

Grades an existing Haytham session by running:
1. Deterministic consistency checks
2. LLM-graded consistency checks (optional)
3. Quality rubric grading (optional)
4. UX transcript grading (optional)

Usage:
    python3 evals/e2e/run_e2e_eval.py --session-dir .haytham/session/
    python3 evals/e2e/run_e2e_eval.py --session-dir .haytham/session/ --transcript transcript.txt
    python3 evals/e2e/run_e2e_eval.py --session-dir .haytham/session/ --full
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared import DEFAULT_GRADING_MODEL

EVALS_DIR = Path(__file__).resolve().parent
EVALS_ROOT = EVALS_DIR.parent
RESULTS_DIR = EVALS_DIR / "results"


def _run_subprocess(cmd: list[str], results_dir: Path,
                    glob_pattern: str) -> dict:
    """Run a subprocess and return parsed results from its output file.

    If the subprocess fails or produces no output file, prints stderr
    and returns an error dict.
    """
    result = subprocess.run(cmd, capture_output=True, text=True)

    if results_dir.exists():
        files = sorted(results_dir.glob(glob_pattern))
        if files:
            return json.loads(files[-1].read_text())

    if result.stderr:
        print(f"  Subprocess error: {result.stderr.strip()}", file=sys.stderr)
    return {"error": result.stderr, "returncode": result.returncode}


def run_consistency_checks(session_dir: str, llm: bool = False,
                           model: str = DEFAULT_GRADING_MODEL) -> dict:
    """Run consistency checks and return parsed results."""
    cmd = [sys.executable, str(EVALS_DIR / "consistency_checks.py"),
           "--session-dir", session_dir]
    if llm:
        cmd.extend(["--llm", "--model", model])
    return _run_subprocess(cmd, EVALS_DIR / "results", "consistency_*.json")


def run_quality_evals(session_dir: str,
                      model: str = DEFAULT_GRADING_MODEL) -> dict:
    """Run quality evals and return parsed results."""
    cmd = [sys.executable, str(EVALS_ROOT / "quality" / "run_quality_evals.py"),
           "--session-dir", session_dir, "--model", model]
    return _run_subprocess(cmd, EVALS_ROOT / "quality" / "results",
                           "quality_*.json")


def run_ux_grading(transcript_path: str,
                   model: str = DEFAULT_GRADING_MODEL) -> dict:
    """Run UX grading and return parsed results."""
    cmd = [sys.executable, str(EVALS_DIR / "ux_grader.py"),
           "--transcript", transcript_path, "--model", model]
    return _run_subprocess(cmd, EVALS_DIR / "results", "ux_*.json")


def main():
    parser = argparse.ArgumentParser(description="Run end-to-end evaluation")
    parser.add_argument("--session-dir", required=True,
                        help="Path to .haytham/session/ directory")
    parser.add_argument("--transcript",
                        help="Path to transcript file for UX grading")
    parser.add_argument("--full", action="store_true",
                        help="Run all evals including LLM-graded checks")
    parser.add_argument("--model", default=DEFAULT_GRADING_MODEL,
                        help="Model for LLM-based grading")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.exists():
        print(f"Session directory not found: {session_dir}")
        sys.exit(1)

    combined = {
        "session_dir": str(session_dir),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": args.model,
        "sections": {},
    }

    # 1. Deterministic consistency checks (always)
    print("=" * 60)
    print("1. Consistency Checks (deterministic)")
    print("=" * 60)
    consistency = run_consistency_checks(str(session_dir), llm=args.full,
                                         model=args.model)
    combined["sections"]["consistency"] = consistency

    # 2. Quality rubric grading (if --full)
    if args.full:
        print("\n" + "=" * 60)
        print("2. Quality Rubric Grading")
        print("=" * 60)
        quality = run_quality_evals(str(session_dir), model=args.model)
        combined["sections"]["quality"] = quality

    # 3. UX grading (if transcript provided)
    if args.transcript:
        print("\n" + "=" * 60)
        print("3. UX Transcript Grading")
        print("=" * 60)
        ux = run_ux_grading(args.transcript, model=args.model)
        combined["sections"]["ux"] = ux

    # Combined summary
    print("\n" + "=" * 60)
    print("E2E Evaluation Summary")
    print("=" * 60)

    for section_name, section_data in combined["sections"].items():
        totals = section_data.get("totals", {})
        if totals:
            parts = [f"{k}: {v}" for k, v in sorted(totals.items()) if v > 0]
            print(f"  {section_name}: {', '.join(parts)}")

    # Save combined results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"e2e_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(combined, indent=2))
    print(f"\nCombined results saved to: {out_file}")


if __name__ == "__main__":
    main()
