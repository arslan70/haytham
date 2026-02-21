"""Factory functions that build ReportConfig from session data.

Each report type (idea validation, MVP spec, etc.) has its own factory
function.  Adding a new report type requires only a new factory here —
zero changes to pdf_report.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .pdf_report import (
    CoverConfig,
    ReportConfig,
    ReportSection,
    SectionType,
)

_HEADING_RE = re.compile(r"^(#{2,3})\s+", re.MULTILINE)

# Keywords for MI sections that overlap with Competitive Landscape
_MI_OVERLAP_KEYWORDS = re.compile(
    r"competitor|competitive|switching|sentiment|opportunit",
    re.IGNORECASE,
)

# Keywords for Concept Expansion sections already rendered elsewhere
_CE_STRIP_KEYWORDS = re.compile(r"Lean Canvas|Concept Health", re.IGNORECASE)

# Confirmation Bias Check / Pre-Submission Validation (metadata, not insight)
_BIAS_CHECK_KEYWORDS = re.compile(r"Confirmation Bias|Pre-Submission", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_sections(text: str, keyword_pattern: re.Pattern[str]) -> str:
    """Remove markdown sections whose headings match a keyword pattern.

    Strips H2/H3 headings and all nested content below them until the
    next heading at the same or higher level.  Used at report-assembly
    time only — session files retain the full text.
    """
    lines = text.split("\n")
    result: list[str] = []
    skip = False
    skip_level = 0
    for line in lines:
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            if keyword_pattern.search(line):
                skip = True
                skip_level = level
                continue
            elif skip and level <= skip_level:
                skip = False
        if not skip:
            result.append(line)
    return "\n".join(result).strip()


def _load_markdown(session_dir: Path, stage_slug: str, filename: str) -> str | None:
    """Load a markdown file from a stage directory, stripping output headers."""
    path = session_dir / stage_slug / filename
    if not path.exists():
        return None
    text = path.read_text()
    # Strip leading "# Output" or "# <Title>" header
    text = re.sub(r"^#+ Output\s*\n+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^# (?!#).+\n+", "", text.strip())
    return text.strip() or None


def _load_system_goal(session_dir: Path) -> str:
    """Load the startup idea text from project.yaml."""
    project_file = session_dir / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return data.get("system_goal", "")
        except (yaml.YAMLError, OSError):
            pass
    return ""


def _extract_verdict(session_dir: Path) -> str | None:
    """Extract recommendation verdict (GO / NO-GO / PIVOT) from recommendation.json."""
    meta_path = session_dir / "recommendation.json"
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            rec = data.get("recommendation", "").upper().strip()
            if rec in ("GO", "NO-GO", "PIVOT"):
                return rec
        except (json.JSONDecodeError, OSError):
            pass
    return None


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_problem_analysis(session_dir: Path) -> ReportSection | None:
    """Build Problem & User Analysis section from concept expansion."""

    text = _load_markdown(session_dir, "idea-analysis", "concept_expansion.md")
    if not text:
        return None
    text = _strip_sections(text, _CE_STRIP_KEYWORDS)
    if not text:
        return None
    return ReportSection("Problem & User Analysis", SectionType.MARKDOWN, text)


def _build_market_context(session_dir: Path) -> ReportSection | None:
    """Build Market Context section."""

    text = _load_markdown(session_dir, "market-context", "market_intelligence.md")
    if not text:
        return None
    # Strip leading "## Market Intelligence" heading (redundant with section title)
    text = re.sub(r"^## Market Intelligence\s*\n+", "", text)
    text = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
    text = _strip_sections(text, _BIAS_CHECK_KEYWORDS)
    if not text:
        return None
    return ReportSection("Market Context", SectionType.MARKDOWN, text)


def _build_competitive_landscape(session_dir: Path) -> ReportSection | None:
    """Build Competitive Landscape section."""

    text = _load_markdown(session_dir, "market-context", "competitor_analysis.md")
    if not text:
        return None
    text = _strip_sections(text, _BIAS_CHECK_KEYWORDS)
    if not text:
        return None
    return ReportSection("Competitive Landscape", SectionType.MARKDOWN, text)


def _build_report_synthesis(session_dir: Path) -> list[ReportSection]:
    """Build sections from the report synthesis markdown.

    The report-synthesis stage produces a single markdown document covering
    all validation findings. This function parses it into sections by H2
    heading so each becomes a separate report section in the PDF.
    """
    text = _load_markdown(session_dir, "report-synthesis", "report_synthesis.md")
    if not text:
        return []

    # Split by ## headings into separate ReportSections
    sections: list[ReportSection] = []
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("## "):
            first_line, _, body = part.partition("\n")
            heading = first_line.lstrip("#").strip()
            if body.strip():
                sections.append(ReportSection(heading, SectionType.MARKDOWN, body.strip()))
        elif not sections:
            # Leading content before first heading (e.g. executive summary)
            sections.append(ReportSection("Overview", SectionType.MARKDOWN, part))

    # If no sections parsed, return the whole text as one section
    if not sections:
        sections.append(ReportSection("Validation Report", SectionType.MARKDOWN, text))

    return sections


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def build_idea_validation_config(session_dir: Path) -> ReportConfig:
    """Build a complete ReportConfig for the Idea Validation report.

    The report is assembled from the upstream analysis stages (idea-analysis,
    market-context) and the report-synthesis stage which produces a single
    markdown document covering risk assessment, scorecard, and next steps.

    Args:
        session_dir: Path to the session directory containing stage outputs.

    Returns:
        ReportConfig ready to pass to generate_pdf().
    """
    idea_text = _load_system_goal(session_dir)
    verdict = _extract_verdict(session_dir)

    cover = CoverConfig(
        title="Idea Validation Report",
        idea_text=idea_text,
        verdict=verdict,
    )

    # Build sections in order
    sections: list[ReportSection] = []

    problem = _build_problem_analysis(session_dir)
    if problem:
        sections.append(problem)

    market = _build_market_context(session_dir)
    if market:
        sections.append(market)

    competitive = _build_competitive_landscape(session_dir)
    if competitive:
        sections.append(competitive)

    # Report synthesis: the single-agent report covering all validation
    # findings, risk assessment, scorecard, and next steps
    sections.extend(_build_report_synthesis(session_dir))

    return ReportConfig(cover=cover, sections=sections)
