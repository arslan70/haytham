#!/usr/bin/env python3
"""UX grader: grades a Haytham run transcript against 7 UX criteria.

Based on commands/ux-review.md criteria.

Usage:
    python3 evals/e2e/ux_grader.py --transcript path/to/transcript.txt
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import anthropic

EVALS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVALS_DIR / "results"

UX_CRITERIA = [
    {
        "id": "ux-1",
        "name": "Roadmap",
        "prompt": "Was a numbered step list shown before any agent was launched? Did it include step names, time estimates, and mark which steps involve user decisions?",
        "anchors": {
            "PASS": "Full roadmap with steps, times, and decision markers",
            "PARTIAL": "Step list shown but missing times or decision markers",
            "FAIL": "No roadmap, or agents launched before any plan was shown",
        },
    },
    {
        "id": "ux-2",
        "name": "Pre-Agent Framing",
        "prompt": "Before each agent call, was there a message explaining what the agent will do and why, in purpose-driven language?",
        "anchors": {
            "PASS": "Every agent call was preceded by a purpose-driven framing message",
            "PARTIAL": "Some agent calls were framed, others were launched without context",
            "FAIL": "Agent calls launched with no framing, or framing was procedural ('Launching agent X')",
        },
    },
    {
        "id": "ux-3",
        "name": "Post-Agent Digest",
        "prompt": "After each agent completed, was there a one-line summary of what was found (read from the output file)?",
        "anchors": {
            "PASS": "Every agent completion followed by a concrete summary of findings",
            "PARTIAL": "Some digests present, others missing or generic ('done')",
            "FAIL": "No post-agent digests, or only generic 'complete' messages",
        },
    },
    {
        "id": "ux-4",
        "name": "Purpose-Driven Transitions",
        "prompt": "Did transition messages explain why the next step exists relative to the user's goal, rather than just naming the step?",
        "anchors": {
            "PASS": "Transitions explain purpose ('Checking if anyone else is solving this')",
            "PARTIAL": "Mix of purpose-driven and procedural transitions",
            "FAIL": "All transitions are procedural ('Moving to Step 3: Research Brief')",
        },
    },
    {
        "id": "ux-5",
        "name": "Guided Review Questions",
        "prompt": "At review/gate steps, were questions specific and actionable with named dimensions to evaluate? Was a low-effort escape provided ('say looks good to continue')?",
        "anchors": {
            "PASS": "Specific dimensions listed, low-effort escape provided",
            "PARTIAL": "Question is specific but missing escape, or has escape but is too open-ended",
            "FAIL": "Open-ended 'anything to correct?' style questions",
        },
    },
    {
        "id": "ux-6",
        "name": "Soft Checkpoint",
        "prompt": "After idea analysis (or the first major agent), was there a visible window for the user to steer without a blocking question?",
        "anchors": {
            "PASS": "Informational pause that signals the user can interject but doesn't require a response",
            "PARTIAL": "Checkpoint present but worded as a blocking question",
            "FAIL": "No checkpoint; system proceeds from first agent directly to next without pause",
        },
    },
    {
        "id": "ux-7",
        "name": "Completion Summary",
        "prompt": "At the end of the phase/workflow, was there a summary noting how many agents ran and how many steps were completed?",
        "anchors": {
            "PASS": "Completion message includes agent/step counts",
            "PARTIAL": "Completion message present but missing counts",
            "FAIL": "No completion summary, or just 'done'",
        },
    },
]


def grade_ux(client: anthropic.Anthropic, transcript: str, model: str) -> list:
    """Grade a transcript against all UX criteria."""
    results = []

    # Truncate very long transcripts to avoid token limits
    if len(transcript) > 50000:
        transcript = transcript[:25000] + "\n\n[...truncated...]\n\n" + transcript[-25000:]

    for criterion in UX_CRITERIA:
        system = (
            "You are grading a Haytham run transcript against UX standards.\n"
            "Respond with valid JSON only: "
            "{\"grade\": \"PASS|PARTIAL|FAIL\", \"evidence\": \"direct quote from transcript\", "
            "\"reasoning\": \"explanation\"}"
        )
        user = (
            f"## Criterion: {criterion['name']}\n\n"
            f"{criterion['prompt']}\n\n"
            f"### Anchors\n"
            f"- PASS: {criterion['anchors']['PASS']}\n"
            f"- PARTIAL: {criterion['anchors']['PARTIAL']}\n"
            f"- FAIL: {criterion['anchors']['FAIL']}\n\n"
            f"### Transcript\n\n{transcript}"
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

        results.append({
            "id": criterion["id"],
            "name": criterion["name"],
            "grade": result.get("grade", "ERROR"),
            "evidence": result.get("evidence", ""),
            "reasoning": result.get("reasoning", ""),
        })
        print(f"  [{result.get('grade', 'ERROR'):7s}] {criterion['name']}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Grade transcript UX")
    parser.add_argument("--transcript", required=True,
                        help="Path to transcript file")
    parser.add_argument("--model", default="claude-opus-4-20250514",
                        help="Model to use for grading")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"Transcript not found: {transcript_path}")
        sys.exit(1)

    transcript = transcript_path.read_text()
    client = anthropic.Anthropic()

    print(f"Grading UX for transcript: {transcript_path}")
    results = grade_ux(client, transcript, args.model)

    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "ERROR": 0}
    for r in results:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1

    print(f"\nUX Score: {counts['PASS']}/7 PASS, {counts['PARTIAL']}/7 PARTIAL, "
          f"{counts['FAIL']}/7 FAIL")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "transcript": str(transcript_path),
        "model": args.model,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totals": counts,
        "criteria_results": results,
    }
    out_file = RESULTS_DIR / f"ux_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(summary, indent=2))
    print(f"Results saved to: {out_file}")


if __name__ == "__main__":
    main()
