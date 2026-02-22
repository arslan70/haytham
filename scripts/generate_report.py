"""Generate a PDF report from existing session data.

Usage:
    uv run python scripts/generate_report.py [--session-dir PATH] [--output PATH]

Reads completed stage outputs from the session directory and renders
the Idea Validation PDF report. No LLM calls, no agents — pure
local rendering from saved data.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from haytham.agents.tools.pdf_report import generate_pdf  # noqa: E402
from haytham.agents.tools.report_configs import build_idea_validation_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PDF report from session data")
    parser.add_argument(
        "--session-dir",
        type=Path,
        default=PROJECT_ROOT / "session",
        help="Path to session directory (default: ./session)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output PDF path (default: ./haytham-idea-validation-report.pdf)",
    )
    args = parser.parse_args()

    session_dir: Path = args.session_dir
    if not session_dir.exists():
        print(f"Error: session directory not found: {session_dir}", file=sys.stderr)
        sys.exit(1)

    report_synthesis_dir = session_dir / "report-synthesis"
    if not report_synthesis_dir.exists():
        print(
            "Error: report-synthesis stage not found. "
            "Run the workflow through report-synthesis first.",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path: Path = args.output or Path("haytham-idea-validation-report.pdf")

    config = build_idea_validation_config(session_dir)
    pdf_bytes = generate_pdf(config)

    output_path.write_bytes(pdf_bytes)
    print(f"Report generated: {output_path} ({len(pdf_bytes):,} bytes)")


if __name__ == "__main__":
    main()
