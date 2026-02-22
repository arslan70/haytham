"""Run DSPy report synthesis for a test idea."""

import json
import os
import sys
from pathlib import Path

import dspy

from tests.dspy_poc.signatures import ReportSynthesis

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OUTPUTS_DIR = Path(__file__).parent / "outputs"
IDEAS_FILE = Path(__file__).parents[1] / "fixtures" / "test_ideas.json"


def load_idea(idea_id: str) -> str:
    """Load the raw idea text from test_ideas.json."""
    with open(IDEAS_FILE) as f:
        data = json.load(f)
    for idea in data["ideas"]:
        if idea["id"] == idea_id:
            return idea["idea"]
    raise ValueError(f"Idea {idea_id} not found in {IDEAS_FILE}")


def load_fixture(idea_id: str, stage: str) -> str:
    """Load upstream fixture output for a given idea and stage."""
    fixture_path = FIXTURES_DIR / idea_id / f"{stage}.md"
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture not found: {fixture_path}\n"
            f"Run the current pipeline for {idea_id} and save fixtures first (see plan Task 3)."
        )
    return fixture_path.read_text()


def synthesize_report(idea_id: str) -> str:
    """Generate a validation report for the given idea using DSPy."""
    model_id = os.environ.get("BEDROCK_HEAVY_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not model_id:
        print("Set BEDROCK_HEAVY_MODEL_ID in .env")
        sys.exit(1)

    lm = dspy.LM(
        f"bedrock/{model_id}",
        region_name=region,
        max_tokens=8000,
    )
    dspy.configure(lm=lm)

    idea = load_idea(idea_id)
    idea_analysis = load_fixture(idea_id, "idea-analysis")
    market_intelligence = load_fixture(idea_id, "market-intelligence")
    competitor_analysis = load_fixture(idea_id, "competitor-analysis")
    market_research = (
        "## Market Intelligence\n\n"
        + market_intelligence
        + "\n\n## Competitor Analysis\n\n"
        + competitor_analysis
    )

    predict = dspy.Predict(ReportSynthesis)
    result = predict(
        idea=idea,
        idea_analysis=idea_analysis,
        market_research=market_research,
    )

    return result.report


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m tests.dspy_poc.synthesize <IDEA_ID>")
        print("Example: python -m tests.dspy_poc.synthesize T1")
        sys.exit(1)

    idea_id = sys.argv[1].upper()
    print(f"Generating report for {idea_id}...")

    report = synthesize_report(idea_id)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / f"{idea_id}_output.md"
    output_path.write_text(report)

    print(f"Report saved to {output_path}")
    print("---")
    print(report)


if __name__ == "__main__":
    main()
