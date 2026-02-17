"""CLI runner for LLM-as-Judge agent evaluation (ADR-018).

Usage:
    python -m haytham.testing.runner
    python -m haytham.testing.runner --agents concept_expansion --ideas T1
    python -m haytham.testing.runner --verbose
    python -m haytham.testing.runner --record --ideas T1
    python -m haytham.testing.runner --use-cached
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from strands_evals import Case, Experiment
from strands_evals.evaluators import OutputEvaluator

from haytham.testing.criteria import (
    AGENT_RUBRICS,
    build_capability_model_cases,
    build_concept_expansion_cases,
    build_story_generator_cases,
    build_system_traits_cases,
)

logger = logging.getLogger(__name__)

# Directories
DEFAULT_FIXTURES_DIR = (
    Path(__file__).parent.parent.parent / "tests" / "fixtures" / "upstream_outputs"
)
CACHED_OUTPUTS_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "agent_outputs"

# All pilot agents
PILOT_AGENTS = ["concept_expansion", "capability_model", "system_traits", "story_generator"]


# =============================================================================
# Agent Task Functions
# =============================================================================


def _extract_agent_output(result) -> str:
    """Extract text from a Strands agent result."""
    from haytham.agents.output_utils import extract_text_from_result

    return extract_text_from_result(result)


def run_concept_expansion(case: Case) -> str:
    """Task function for concept_expansion agent."""
    from haytham.agents.factory.agent_factory import create_agent_by_name

    agent = create_agent_by_name("concept_expansion")
    query = (
        "Analyze this startup idea in depth. Identify the core problems it solves, "
        f"target users, and unique value proposition: {case.input}"
    )
    result = agent(query)
    return _extract_agent_output(result)


def run_capability_model(case: Case) -> str:
    """Task function for capability_model agent."""
    from haytham.agents.factory.agent_factory import create_agent_by_name

    agent = create_agent_by_name("capability_model")
    result = agent(case.input)
    return _extract_agent_output(result)


def run_system_traits(case: Case) -> str:
    """Task function for system_traits agent."""
    from haytham.agents.factory.agent_factory import create_agent_by_name

    agent = create_agent_by_name("system_traits")
    result = agent(case.input)
    return _extract_agent_output(result)


def run_story_generator(case: Case) -> str:
    """Task function for story_generator — uses run_story_swarm."""
    from haytham.agents.worker_story_generator.story_swarm import run_story_swarm

    meta = case.metadata
    markdown, _ = run_story_swarm(
        mvp_scope=meta["mvp_scope"],
        capability_model=meta["capability_model"],
        architecture_decisions=meta["architecture_decisions"],
        build_buy_analysis=meta["build_buy_analysis"],
        system_goal=meta.get("system_goal", ""),
    )
    return markdown


# Map agent names to their task functions
TASK_FUNCTIONS = {
    "concept_expansion": run_concept_expansion,
    "capability_model": run_capability_model,
    "system_traits": run_system_traits,
    "story_generator": run_story_generator,
}

# Map agent names to their case builder functions
CASE_BUILDERS = {
    "concept_expansion": lambda ids, fixtures_dir: build_concept_expansion_cases(ids),
    "capability_model": lambda ids, fixtures_dir: build_capability_model_cases(ids, fixtures_dir),
    "system_traits": lambda ids, fixtures_dir: build_system_traits_cases(ids, fixtures_dir),
    "story_generator": lambda ids, fixtures_dir: build_story_generator_cases(ids, fixtures_dir),
}


# =============================================================================
# Cached Output Support
# =============================================================================


def _get_cached_output_path(agent_name: str, idea_id: str) -> Path:
    """Get the path for a cached agent output."""
    return CACHED_OUTPUTS_DIR / agent_name / f"{idea_id}.md"


def _save_cached_output(agent_name: str, idea_id: str, output: str) -> None:
    """Save an agent output to the cache directory."""
    path = _get_cached_output_path(agent_name, idea_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output)
    logger.info(f"Cached output saved: {path}")


def _load_cached_output(agent_name: str, idea_id: str) -> str | None:
    """Load a cached agent output, or None if not found."""
    path = _get_cached_output_path(agent_name, idea_id)
    if path.exists():
        return path.read_text()
    return None


# =============================================================================
# Evaluation Runner
# =============================================================================


def run_evaluation(
    agent_name: str,
    idea_ids: list[str],
    fixtures_dir: Path,
    verbose: bool = False,
    use_cached: bool = False,
) -> dict:
    """Run evaluation for a single agent across specified ideas.

    Returns dict with:
        agent_name: str
        results: list of {idea_id, category, passed, score, reason}
        pass_count: int
        fail_count: int
        skip_count: int
        error_count: int
    """
    config = AGENT_RUBRICS.get(agent_name)
    if config is None:
        return {
            "agent_name": agent_name,
            "results": [],
            "pass_count": 0,
            "fail_count": 0,
            "skip_count": 0,
            "error_count": 1,
            "error": f"Unknown agent: {agent_name}",
        }

    # Build cases
    case_builder = CASE_BUILDERS.get(agent_name)
    if case_builder is None:
        return {
            "agent_name": agent_name,
            "results": [],
            "pass_count": 0,
            "fail_count": 0,
            "skip_count": 0,
            "error_count": 1,
            "error": f"No case builder for agent: {agent_name}",
        }

    cases = case_builder(idea_ids, fixtures_dir)

    if not cases:
        skipped_ids = ", ".join(idea_ids)
        return {
            "agent_name": agent_name,
            "results": [],
            "pass_count": 0,
            "fail_count": 0,
            "skip_count": len(idea_ids),
            "error_count": 0,
            "warning": f"No test cases built (missing fixtures for {skipped_ids})",
        }

    # Build evaluator
    evaluator = OutputEvaluator(
        rubric=config.rubric,
        include_inputs=True,
    )

    results = []

    for case in cases:
        idea_id = case.metadata.get("idea_id", "??")
        category = case.metadata.get("category", "Unknown")

        try:
            # Get agent output (cached or fresh)
            if use_cached:
                output = _load_cached_output(agent_name, idea_id)
                if output is None:
                    results.append(
                        {
                            "idea_id": idea_id,
                            "category": category,
                            "passed": None,
                            "score": None,
                            "reason": "No cached output found",
                            "status": "skip",
                        }
                    )
                    continue
            else:
                # Run the agent
                task_fn = TASK_FUNCTIONS[agent_name]
                output = task_fn(case)

                # Cache the output for future --use-cached runs
                _save_cached_output(agent_name, idea_id, output)

            # Evaluate with OutputEvaluator
            single_experiment = Experiment(
                cases=[
                    Case(
                        input=case.input,
                        expected_output=case.expected_output,
                        metadata=case.metadata,
                    )
                ],
                evaluators=[evaluator],
            )

            # Create a wrapper that returns the pre-computed output
            def _cached_task(c: Case, _output=output) -> str:
                return _output

            reports = single_experiment.run_evaluations(_cached_task)

            # Extract evaluation result from EvaluationReport
            # API: report.scores[i], report.test_passes[i], report.reasons[i]
            if reports and reports[0].scores:
                report = reports[0]
                score = report.scores[0]
                reason = report.reasons[0] if report.reasons else ""
                passed = score >= config.pass_threshold

                results.append(
                    {
                        "idea_id": idea_id,
                        "category": category,
                        "passed": passed,
                        "score": score,
                        "reason": reason,
                        "status": "pass" if passed else "fail",
                    }
                )
            else:
                results.append(
                    {
                        "idea_id": idea_id,
                        "category": category,
                        "passed": None,
                        "score": None,
                        "reason": "No evaluation result returned",
                        "status": "error",
                    }
                )

        except Exception as e:
            logger.error(f"Error evaluating {agent_name}/{idea_id}: {e}", exc_info=True)
            results.append(
                {
                    "idea_id": idea_id,
                    "category": category,
                    "passed": None,
                    "score": None,
                    "reason": f"ERROR: {e}",
                    "status": "error",
                }
            )

    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    skip_count = sum(1 for r in results if r["status"] == "skip")
    error_count = sum(1 for r in results if r["status"] == "error")

    return {
        "agent_name": agent_name,
        "results": results,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "skip_count": skip_count,
        "error_count": error_count,
    }


# =============================================================================
# Fixture Recording
# =============================================================================


def record_fixtures(idea_id: str, session_dir: Path | None = None) -> None:
    """Record upstream fixtures from a completed session.

    Copies stage outputs from session/ into tests/fixtures/upstream_outputs/{idea_id}/.
    """
    if session_dir is None:
        session_dir = Path.cwd() / "session"

    target_dir = DEFAULT_FIXTURES_DIR / idea_id
    target_dir.mkdir(parents=True, exist_ok=True)

    # Map stage slugs to fixture filenames
    stage_fixture_map = {
        "mvp-scope": "mvp-scope.md",
        "capability-model": "capability-model.md",
        "system-traits": "system-traits.md",
        "architecture-decisions": "architecture-decisions.md",
        "build-buy-analysis": "build-buy-analysis.md",
    }

    recorded = []
    missing = []

    for stage_slug, fixture_name in stage_fixture_map.items():
        stage_dir = session_dir / stage_slug
        if not stage_dir.exists():
            missing.append(stage_slug)
            continue

        # Find the output markdown file in the stage directory
        md_files = list(stage_dir.glob("*.md"))
        if not md_files:
            missing.append(stage_slug)
            continue

        # Use the first (or only) markdown file
        source = md_files[0]
        target = target_dir / fixture_name
        shutil.copy2(source, target)
        recorded.append(fixture_name)
        print(f"  Recorded: {source} -> {target}")

    if recorded:
        print(f"\nRecorded {len(recorded)} fixtures for {idea_id}")
    if missing:
        print(f"Missing stages (not yet run?): {', '.join(missing)}")


# =============================================================================
# Report Formatting
# =============================================================================


def format_report(all_results: list[dict], verbose: bool = False) -> str:
    """Format evaluation results as a readable report."""
    lines = []
    lines.append("")
    lines.append("=== Haytham Agent Quality Report ===")
    lines.append("")

    total_pass = 0
    total_fail = 0
    total_skip = 0
    total_error = 0

    for agent_result in all_results:
        agent_name = agent_result["agent_name"]
        lines.append(agent_name)

        if "error" in agent_result:
            lines.append(f"  ERROR: {agent_result['error']}")
            total_error += 1
            lines.append("")
            continue

        if "warning" in agent_result:
            lines.append(f"  SKIP: {agent_result['warning']}")
            total_skip += agent_result["skip_count"]
            lines.append("")
            continue

        for r in agent_result["results"]:
            idea_id = r["idea_id"]
            category = r["category"]
            status = r["status"].upper()

            if r["score"] is not None:
                score_str = f"score={r['score']:.2f}"
            else:
                score_str = "score=N/A"

            lines.append(f"  {idea_id} ({category}):  {status}  {score_str}")

            if verbose and r.get("reason"):
                # Indent the reason text
                for reason_line in r["reason"].split("\n"):
                    lines.append(f"    {reason_line}")

        total_pass += agent_result["pass_count"]
        total_fail += agent_result["fail_count"]
        total_skip += agent_result["skip_count"]
        total_error += agent_result["error_count"]
        lines.append("")

    total = total_pass + total_fail + total_skip + total_error
    lines.append(
        f"Summary: {total_pass}/{total} PASS",
    )
    if total_fail:
        lines.append(f"  {total_fail} FAIL")
    if total_skip:
        lines.append(f"  {total_skip} SKIP")
    if total_error:
        lines.append(f"  {total_error} ERROR")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> None:
    """CLI entry point for agent evaluation."""
    parser = argparse.ArgumentParser(
        description="Haytham Agent Quality Evaluation (ADR-018)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--agents",
        type=str,
        default=",".join(PILOT_AGENTS),
        help="Comma-separated agent names (default: all 3 pilots)",
    )
    parser.add_argument(
        "--ideas",
        type=str,
        default="T1,T2",
        help="Comma-separated idea IDs (default: T1,T2)",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=str,
        default=str(DEFAULT_FIXTURES_DIR),
        help="Path to upstream fixtures directory",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-case reasoning from the judge",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record session outputs as fixtures (use with --ideas)",
    )
    parser.add_argument(
        "--use-cached",
        action="store_true",
        help="Re-judge cached outputs without re-running agents",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Handle --record mode
    if args.record:
        idea_ids = [i.strip() for i in args.ideas.split(",")]
        for idea_id in idea_ids:
            print(f"Recording fixtures for {idea_id}...")
            record_fixtures(idea_id)
        return

    # Parse arguments
    agent_names = [a.strip() for a in args.agents.split(",")]
    idea_ids = [i.strip() for i in args.ideas.split(",")]
    fixtures_dir = Path(args.fixtures_dir)

    # Validate agent names
    for name in agent_names:
        if name not in AGENT_RUBRICS:
            print(f"ERROR: Unknown agent '{name}'. Available: {', '.join(AGENT_RUBRICS.keys())}")
            sys.exit(1)

    # Run evaluations
    all_results = []
    for agent_name in agent_names:
        print(f"Evaluating {agent_name}...")
        result = run_evaluation(
            agent_name=agent_name,
            idea_ids=idea_ids,
            fixtures_dir=fixtures_dir,
            verbose=args.verbose,
            use_cached=args.use_cached,
        )
        all_results.append(result)

    # Print report
    report = format_report(all_results, verbose=args.verbose)
    print(report)

    # Exit with non-zero if any failures
    total_fail = sum(r["fail_count"] for r in all_results)
    total_error = sum(r["error_count"] for r in all_results)
    if total_fail > 0 or total_error > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
